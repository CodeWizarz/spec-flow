import { makeAutoObservable, runInAction } from "mobx";
import { SignalService } from "@plane/services";

export class SignalStore {
  signals: any[] = [];
  isLoading: boolean = false;
  error: string | null = null;
  signalService: any; // Using local relative resolution or plane/services type depending on build

  constructor() {
    makeAutoObservable(this);
    // Ideally inject the service, initializing for now
    this.signalService = new SignalService();
  }

  fetchSignals = async (workspaceSlug: string) => {
    this.isLoading = true;
    try {
      const response = await this.signalService.getSignals(workspaceSlug);
      runInAction(() => {
        this.signals = response;
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

  createSignal = async (workspaceSlug: string, formData: FormData) => {
    this.isLoading = true;
    try {
      const newSignal = await this.signalService.createSignal(workspaceSlug, formData);
      runInAction(() => {
        this.signals.unshift(newSignal);
        this.error = null;
      });
      return newSignal;
    } catch (error: any) {
      runInAction(() => {
        this.error = error.message;
      });
      throw error;
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };
}
