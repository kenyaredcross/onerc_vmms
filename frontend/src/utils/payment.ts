import { initSocket } from "../socket";

export type PaymentResult = "Completed" | "Failed" | "Timeout";

interface StkPaymentEvent {
  status?: string;
  expected_token?: string;
}

class PaymentListener {
  private MEMBERSHIP_PAYMENT_KEY = "mp_token";
  private SOCKET_EVENT = "stk_payment_complete";

 
  private TIMEOUT_MS = 150000;

  saveToken(token: string): void {
    sessionStorage.setItem(this.MEMBERSHIP_PAYMENT_KEY, token);
  }

  getToken(): string {
    return sessionStorage.getItem(this.MEMBERSHIP_PAYMENT_KEY) || "";
  }

  hasPendingPayment(): boolean {
    return Boolean(this.getToken());
  }

  private clearToken(): void {
    sessionStorage.removeItem(this.MEMBERSHIP_PAYMENT_KEY);
  }

  listenForPayment(token?: string): Promise<PaymentResult> {
    const expectedToken = token || this.getToken();

    if (!expectedToken) {
      return Promise.resolve("Failed");
    }

    const $socket = initSocket();

    return new Promise((resolve) => {
      let settled = false;

      const finish = (status: PaymentResult) => {
        if (settled) return;
        settled = true;

        clearTimeout(timer);
      
        $socket.off(this.SOCKET_EVENT, handler);
        this.clearToken();

        resolve(status);
      };

      const handler = (data: StkPaymentEvent) => {
       
        if (data?.expected_token !== expectedToken) return;

        finish(data.status === "Completed" ? "Completed" : "Failed");
      };

      const timer = setTimeout(() => finish("Timeout"), this.TIMEOUT_MS);

      $socket.on(this.SOCKET_EVENT, handler);
    });
  }
}

export const paymentListener = new PaymentListener();
