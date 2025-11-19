// Offline request queue manager
type QueuedRequest = {
  id: string;
  url: string;
  method: string;
  headers: Record<string, string>;
  body?: string;
  timestamp: number;
  retries: number;
};

class OfflineManager {
  private static instance: OfflineManager;
  private queue: QueuedRequest[] = [];
  private readonly MAX_RETRIES = 3;
  private readonly QUEUE_KEY = 'yourdaddy-offline-queue';
  private isProcessing = false;

  private constructor() {
    this.loadQueue();
    // Listen for online/offline events
    window.addEventListener('online', () => this.processQueue());
  }

  static getInstance(): OfflineManager {
    if (!OfflineManager.instance) {
      OfflineManager.instance = new OfflineManager();
    }
    return OfflineManager.instance;
  }

  private loadQueue() {
    try {
      const stored = localStorage.getItem(this.QUEUE_KEY);
      if (stored) {
        this.queue = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Failed to load offline queue:', error);
      this.queue = [];
    }
  }

  private saveQueue() {
    try {
      localStorage.setItem(this.QUEUE_KEY, JSON.stringify(this.queue));
    } catch (error) {
      console.error('Failed to save offline queue:', error);
    }
  }

  queueRequest(url: string, options: RequestInit = {}): string {
    const id = `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const queuedRequest: QueuedRequest = {
      id,
      url,
      method: options.method || 'GET',
      headers: (options.headers as Record<string, string>) || {},
      body: options.body as string | undefined,
      timestamp: Date.now(),
      retries: 0,
    };

    this.queue.push(queuedRequest);
    this.saveQueue();
    
    console.log(`Request queued for offline: ${id}`);
    return id;
  }

  async processQueue() {
    if (this.isProcessing || !navigator.onLine) {
      return;
    }

    this.isProcessing = true;
    console.log(`Processing offline queue: ${this.queue.length} requests`);

    const failed: QueuedRequest[] = [];

    for (const request of this.queue) {
      try {
        const response = await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: request.body,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        console.log(`Successfully processed queued request: ${request.id}`);
      } catch (error) {
        console.error(`Failed to process queued request ${request.id}:`, error);
        
        request.retries++;
        if (request.retries < this.MAX_RETRIES) {
          failed.push(request);
        } else {
          console.warn(`Request ${request.id} exceeded max retries, discarding`);
        }
      }
    }

    this.queue = failed;
    this.saveQueue();
    this.isProcessing = false;

    if (this.queue.length > 0) {
      console.log(`${this.queue.length} requests remain in queue`);
    } else {
      console.log('Offline queue cleared');
    }
  }

  getQueueSize(): number {
    return this.queue.length;
  }

  clearQueue() {
    this.queue = [];
    this.saveQueue();
  }
}

export default OfflineManager;
