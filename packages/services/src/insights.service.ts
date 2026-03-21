import { APIService } from "./api.service";

export class InsightService extends APIService {
  constructor() {
    super(process.env.NEXT_PUBLIC_API_BASE_URL || "");
  }

  async getInsights(workspaceSlug: string): Promise<any[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/insights/`)
      .then((res) => res.data)
      .catch((err) => {
        throw err;
      });
  }

  async generateInsights(workspaceSlug: string): Promise<any> {
    return this.post(`/api/workspaces/${workspaceSlug}/signals/generate/`)
      .then((res) => res.data)
      .catch((err) => {
        throw err;
      });
  }
}
