import { makeAutoObservable, runInAction } from "mobx";
import { SpecService } from "@plane/services";

export class SpecStore {
  specs: any[] = [];
  isLoading: boolean = false;
  isGenerating: boolean = false;
  error: string | null = null;
  specService: any;

  constructor() {
    makeAutoObservable(this);
    this.specService = new SpecService();
  }

  fetchSpecs = async (workspaceSlug: string) => {
    this.isLoading = true;
    try {
      const response = await this.specService.getSpecs(workspaceSlug);
      runInAction(() => {
        this.specs = response;
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

  generateSpec = async (workspaceSlug: string, insightIds?: string[]) => {
    this.isGenerating = true;
    try {
      await this.specService.generateSpec(workspaceSlug, insightIds);
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
