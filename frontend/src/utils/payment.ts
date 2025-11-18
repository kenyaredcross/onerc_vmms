import { initSocket } from "../socket";

export class PaymentListener {
  private TOKEN_KEY = "pt_ticket";
  private SOCKET_EVENT = "stk_payment_complete";
  private expectedToken = "";

  constructor() {
    this.getToken();
  }

  saveToken(token: string) {
    sessionStorage.setItem(this.TOKEN_KEY, token);
    this.expectedToken = token;
  }

  private getToken(): void {
    this.expectedToken = sessionStorage.getItem(this.TOKEN_KEY) || "";
  }

  private clearToken(): void {
    sessionStorage.removeItem(this.TOKEN_KEY);
  }

  listenForPayment(): Promise<string> {
    const socket = initSocket();

    return new Promise((resolve) => {
      socket.on(this.SOCKET_EVENT, (data) => {
        if (data?.expected_token === this.expectedToken) {
          const status = data.status;

          this.clearToken();
          socket.off(this.SOCKET_EVENT);

          resolve(status);
        }
      });
    });
  }
}
