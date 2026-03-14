import { initSocket } from "../socket";

class PaymentListener {
  private MEMBERSHIP_PAYMENT_KEY = "mp_token";
  private SOCKET_EVENT = "stk_payment_complete";
  private expectedToken = "";

  constructor() {
    this.getToken();
  }

  saveToken(token: string) {
    sessionStorage.setItem(this.MEMBERSHIP_PAYMENT_KEY, token);
    this.expectedToken = token;
  }

  private getToken(): void {
    this.expectedToken =
      sessionStorage.getItem(this.MEMBERSHIP_PAYMENT_KEY) || "";
  }

  private clearToken(): void {
    sessionStorage.removeItem(this.MEMBERSHIP_PAYMENT_KEY);
  }

  listenForPayment(): Promise<string> {
    const $socket = initSocket();

    return new Promise((resolve) => {
      $socket.on(this.SOCKET_EVENT, (data) => {
        if (data?.expected_token === this.expectedToken) {
          const status = data.status;

          this.clearToken();
          $socket.off(this.SOCKET_EVENT);

          resolve(status);
        }
      });
    });
  }
}

export const paymentListener = new PaymentListener();
