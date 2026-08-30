param(
	[Parameter(Mandatory = $true)]
	[string]$Url,

	[Parameter(Mandatory = $true)]
	[string]$Output,

	[int]$Width = 1440,
	[int]$Height = 1000,
	[int]$WaitMilliseconds = 8000,
	[switch]$Mobile,
	[switch]$FullPage,
	[ValidateSet("", "signup-sent", "expired-password-link")]
	[string]$Prepare = "",
	[string]$Edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

$ErrorActionPreference = "Stop"
$script:CdpSequence = 0
$script:CdpEvents = @()
$port = Get-Random -Minimum 9400 -Maximum 9999
$profile = "C:\Windows\Temp\vmms-redesign-cdp-$PID"
$browser = $null
$socket = $null

function Get-DevToolsTarget {
	param([int]$DebugPort)

	$lastError = $null
	for ($attempt = 0; $attempt -lt 80; $attempt += 1) {
		try {
			$targets = Invoke-RestMethod -Uri "http://127.0.0.1:$DebugPort/json/list" -TimeoutSec 1
			$target = $targets | Where-Object { $_.type -eq "page" } | Select-Object -First 1
			if ($target.webSocketDebuggerUrl) { return $target }
		} catch {
			$lastError = $_.Exception.Message
		}

		Start-Sleep -Milliseconds 250
	}

	throw "Edge DevTools did not become ready: $lastError"
}

function Receive-CdpMessage {
	param([System.Net.WebSockets.ClientWebSocket]$Client)

	$stream = New-Object System.IO.MemoryStream
	try {
		do {
			$buffer = New-Object byte[] 65536
			$segment = New-Object System.ArraySegment[byte] -ArgumentList @(,$buffer)
			$result = $Client.ReceiveAsync(
				$segment,
				[System.Threading.CancellationToken]::None
			).GetAwaiter().GetResult()

			if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
				throw "DevTools closed the socket before replying"
			}

			$stream.Write($buffer, 0, $result.Count)
		} while (-not $result.EndOfMessage)

		return [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
	} finally {
		$stream.Dispose()
	}
}

function Invoke-Cdp {
	param(
		[System.Net.WebSockets.ClientWebSocket]$Client,
		[string]$Method,
		[hashtable]$Parameters = @{}
	)

	$script:CdpSequence += 1
	$id = $script:CdpSequence
	$payload = @{
		id = $id
		method = $Method
		params = $Parameters
	} | ConvertTo-Json -Depth 20 -Compress
	$bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
	$segment = New-Object System.ArraySegment[byte] -ArgumentList @(,$bytes)

	$Client.SendAsync(
		$segment,
		[System.Net.WebSockets.WebSocketMessageType]::Text,
		$true,
		[System.Threading.CancellationToken]::None
	).GetAwaiter().GetResult() | Out-Null

	do {
		$message = Receive-CdpMessage -Client $Client | ConvertFrom-Json
		if (-not $message.id -and $message.method) {
			$script:CdpEvents += $message
		}
	} while ($message.id -ne $id)

	if ($message.error) {
		throw "$($message.error.message) ($($message.error.code))"
	}

	return $message.result
}

try {
	$arguments = @(
		"--headless=new",
		"--disable-gpu",
		"--hide-scrollbars",
		"--no-first-run",
		"--disable-default-apps",
		"--disable-sync",
		"--remote-debugging-port=$port",
		"--remote-debugging-address=127.0.0.1",
		"--remote-allow-origins=*",
		"--user-data-dir=$profile",
		"about:blank"
	)

	$browser = Start-Process -FilePath $Edge -ArgumentList $arguments -PassThru -WindowStyle Hidden
	$target = Get-DevToolsTarget -DebugPort $port
	$socket = New-Object System.Net.WebSockets.ClientWebSocket
	$socket.ConnectAsync(
		[Uri]$target.webSocketDebuggerUrl,
		[System.Threading.CancellationToken]::None
	).GetAwaiter().GetResult() | Out-Null

	Invoke-Cdp -Client $socket -Method "Page.enable" | Out-Null
	Invoke-Cdp -Client $socket -Method "Runtime.enable" | Out-Null
	Invoke-Cdp -Client $socket -Method "Emulation.setDeviceMetricsOverride" -Parameters @{
		width = $Width
		height = $Height
		deviceScaleFactor = 1
		mobile = [bool]$Mobile
		fitWindow = $false
		screenWidth = $Width
		screenHeight = $Height
	} | Out-Null

	if ($Mobile) {
		Invoke-Cdp -Client $socket -Method "Emulation.setUserAgentOverride" -Parameters @{
			userAgent = "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
			platform = "Android"
		} | Out-Null
		Invoke-Cdp -Client $socket -Method "Emulation.setTouchEmulationEnabled" -Parameters @{
			enabled = $true
			maxTouchPoints = 5
		} | Out-Null
	}

	Invoke-Cdp -Client $socket -Method "Page.navigate" -Parameters @{ url = $Url } | Out-Null
	Start-Sleep -Milliseconds $WaitMilliseconds

	# Reveal a state that already exists in the rendered page without performing
	# its external side effect. This is deliberately a closed set rather than an
	# arbitrary JavaScript argument: captures may inspect UI state, never gain a
	# general-purpose execution flag. The reserved `.invalid` address cannot be a
	# real applicant and no account or email request is made.
	if ($Prepare -eq "signup-sent") {
		$prepareExpression = @'
(() => {
	const start = document.querySelector(".signup-start");
	const sent = document.querySelector(".signup-sent");
	if (!start || !sent) throw new Error("signup-sent state is not available on this page");

	start.classList.add("hidden");
	sent.classList.remove("hidden");
	sent.querySelector(".signup-sent-email").textContent = "applicant@example.invalid";
	sent.querySelector(".signup-resend")?.classList.remove("hidden");
	const button = sent.querySelector(".btn-resend-signup");
	if (button) button.disabled = true;
	const cooldown = sent.querySelector(".auth-cooldown");
	if (cooldown) {
		cooldown.textContent = "You can ask for another link in 60s.";
		cooldown.classList.remove("hidden");
	}
})()
'@
		Invoke-Cdp -Client $socket -Method "Runtime.evaluate" -Parameters @{
			expression = $prepareExpression
		} | Out-Null
	}

	if ($Prepare -eq "expired-password-link") {
		$prepareExpression = @'
(async () => {
	const form = document.querySelector("#reset-password");
	const password = "Capture-only9!";
	if (!form) throw new Error("password-reset state is not available on this page");

	for (const id of ["new_password", "confirm_password"]) {
		const input = document.getElementById(id);
		if (!input) throw new Error(`${id} is not available on this page`);
		input.value = password;
		input.dispatchEvent(new Event("input", { bubbles: true }));
		input.dispatchEvent(new Event("keyup", { bubbles: true }));
	}

	form.requestSubmit();
	await new Promise((resolve) => setTimeout(resolve, 1800));
	window.scrollTo(0, 0);
})()
'@
		Invoke-Cdp -Client $socket -Method "Runtime.evaluate" -Parameters @{
			expression = $prepareExpression
			awaitPromise = $true
		} | Out-Null
	}

	# A full-page screenshot includes content below the CSS viewport, but the
	# browser does not consider that content visible for native lazy loading.
	# Walk the document once before measuring it so real below-the-fold images are
	# present in the evidence instead of appearing as empty capture-only boxes.
	if ($FullPage) {
		$scrollExpression = @'
(async () => {
	const step = Math.max(Math.round(innerHeight * 0.75), 400);
	for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
		window.scrollTo(0, y);
		await new Promise((resolve) => setTimeout(resolve, 90));
	}
	window.scrollTo(0, 0);
	await new Promise((resolve) => setTimeout(resolve, 300));
})()
'@
		Invoke-Cdp -Client $socket -Method "Runtime.evaluate" -Parameters @{
			expression = $scrollExpression
			awaitPromise = $true
		} | Out-Null
	}

	$expression = @'
JSON.stringify({
	url: location.href,
	title: document.title,
	innerWidth,
	innerHeight,
	clientWidth: document.documentElement.clientWidth,
	scrollWidth: document.documentElement.scrollWidth,
	scrollHeight: document.documentElement.scrollHeight,
	bodyScrollWidth: document.body ? document.body.scrollWidth : 0,
	overflowing: Array.from(document.querySelectorAll("body *"))
		.map((element) => {
			const rect = element.getBoundingClientRect();
			return {
				tag: element.tagName.toLowerCase(),
				className: typeof element.className === "string" ? element.className.slice(0, 180) : "",
				text: (element.innerText || "").replace(/\s+/g, " ").trim().slice(0, 100),
				left: Math.round(rect.left),
				right: Math.round(rect.right),
				width: Math.round(rect.width)
			};
		})
		.filter((item) => item.left < -1 || item.right > document.documentElement.clientWidth + 1)
		.slice(0, 25),
	bodyText: (document.body ? document.body.innerText : "").slice(0, 500)
})
'@
	$evaluation = Invoke-Cdp -Client $socket -Method "Runtime.evaluate" -Parameters @{
		expression = $expression
		returnByValue = $true
	}
	$page = $evaluation.result.value | ConvertFrom-Json
	$runtimeEvents = @(
		$script:CdpEvents |
			Where-Object {
				$_.method -eq "Runtime.exceptionThrown" -or
				$_.method -eq "Runtime.consoleAPICalled" -or
				$_.method -eq "Log.entryAdded"
			} |
			ForEach-Object {
				$text = if ($_.method -eq "Runtime.exceptionThrown") {
					$_.params.exceptionDetails.exception.description
				} elseif ($_.method -eq "Runtime.consoleAPICalled") {
					($_.params.args | ForEach-Object { $_.value }) -join " "
				} else {
					$_.params.entry.text
				}

				[ordered]@{
					method = $_.method
					text = [string]$text
				}
			}
	)
	$screenshotHeight = if ($FullPage) {
		[Math]::Min([int]$page.scrollHeight, 12000)
	} else {
		$Height
	}

	$capture = Invoke-Cdp -Client $socket -Method "Page.captureScreenshot" -Parameters @{
		format = "png"
		fromSurface = $true
		captureBeyondViewport = [bool]$FullPage
		clip = @{
			x = 0
			y = 0
			width = $Width
			height = $screenshotHeight
			scale = 1
		}
	}

	[System.IO.File]::WriteAllBytes($Output, [Convert]::FromBase64String($capture.data))

	[ordered]@{
		url = $page.url
		title = $page.title
		innerWidth = $page.innerWidth
		innerHeight = $page.innerHeight
		clientWidth = $page.clientWidth
		scrollWidth = $page.scrollWidth
		scrollHeight = $page.scrollHeight
		bodyScrollWidth = $page.bodyScrollWidth
		overflowing = $page.overflowing
		bodyText = $page.bodyText
		runtimeEvents = $runtimeEvents
		requestedWidth = $Width
		requestedHeight = $Height
		mobile = [bool]$Mobile
		fullPage = [bool]$FullPage
		prepare = $Prepare
		output = $Output
	} | ConvertTo-Json -Depth 5

	try {
		Invoke-Cdp -Client $socket -Method "Browser.close" | Out-Null
	} catch {
		# Closing the browser can close the socket before its acknowledgement.
	}
} finally {
	if ($socket) { $socket.Dispose() }
	if ($browser -and -not $browser.HasExited) {
		Stop-Process -Id $browser.Id -Force -ErrorAction SilentlyContinue
	}
	try {
		if (Test-Path $profile) {
			Remove-Item -Path $profile -Recurse -Force -ErrorAction Stop
		}
	} catch {
		# Edge child processes can hold a profile file briefly after Browser.close.
		# It lives in Windows Temp and is safe for the OS to collect later.
	}
}
