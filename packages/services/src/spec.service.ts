import { APIService } from "./api.service";

export class SpecService extends APIService {
  constructor() {
    super(process.env.NEXT_PUBLIC_API_BASE_URL || "");
  }

  async getSpecs(workspaceSlug: string): Promise<any[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/specs/`)
      .then((res) => res.data)
      .catch((err) => {
        throw err;
      });
  }

  async generateSpec(workspaceSlug: string, insightIds?: string[]): Promise<any> {
    return this.post(`/api/workspaces/${workspaceSlug}/specs/generate/`, {
      insight_ids: insightIds,
    })
      .then((res) => res.data)
      .catch((err) => {
        throw err;
      });
  }
}
