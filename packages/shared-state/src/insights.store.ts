import { makeAutoObservable, runInAction } from "mobx";
import { InsightService } from "@plane/services";

export class InsightStore {
  insights: any[] = [];
  isLoading: boolean = false;
  isGenerating: boolean = false;
  error: string | null = null;
  insightService: any;

  constructor() {
    makeAutoObservable(this);
    this.insightService = new InsightService();
  }

  fetchInsights = async (workspaceSlug: string) => {
    this.isLoading = true;
    try {
      const response = await this.insightService.getInsights(workspaceSlug);
      runInAction(() => {
        this.insights = response;
        this.error = null;
      });
    } catch (error: any) {
      runInAction(() => {
        this.error = error.message;
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  generateInsights = async (workspaceSlug: string) => {
    this.isGenerating = true;
    try {
      await this.insightService.generateInsights(workspaceSlug);
      // Wait a bit before polling or rely on user refreshing for MVP
      runInAction(() => {
        this.error = null;
      });
    } catch (error: any) {
      runInAction(() => {
        this.error = error.message;
      });
      throw error;
    } finally {
      runInAction(() => {
        this.isGenerating = false;
      });
    }
  };
}
