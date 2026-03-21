import { APIService } from "./api.service";

export class SignalService extends APIService {
  constructor() {
    super(process.env.NEXT_PUBLIC_API_BASE_URL || "");
  }

  async getSignals(workspaceSlug: string): Promise<any[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/signals/`)
      .then((res) => res.data)
      .catch((err) => {
        throw err;
      });
  }

  async createSignal(workspaceSlug: string, formData: FormData): Promise<any> {
    return this.post(`/api/workspaces/${workspaceSlug}/signals/`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
      .then((res) => res.data)
      .catch((err) => {
        throw err;
      });
  }
}
