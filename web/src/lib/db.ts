import Dexie, { type Table } from "dexie";

// Offline-first capture queue. Logs are written here instantly, then synced to the API.
export interface QueuedCapture {
  id?: number;
  text: string;
  occurred_at: string;
  domain_hint?: string;
  source: string;
  media_keys: string[];
  created_at: string;
  synced: 0 | 1;
}

class LifeOSDB extends Dexie {
  captures!: Table<QueuedCapture, number>;

  constructor() {
    super("lifeos");
    this.version(1).stores({ captures: "++id, synced, created_at" });
  }
}

export const db = new LifeOSDB();
