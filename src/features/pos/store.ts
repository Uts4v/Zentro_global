import { create } from "zustand";
import {
  PosBootstrapResponse,
  PosDevice,
  PosOrder,
  PosReceiptData,
  PosSettings,
  ShiftWorker,
  CashShift,
  PosMenuSnapshot,
} from "./api";

type PosOrderItem = {
  menu_item_id: number;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
};

interface PosState {
  merchant: { id: number; business_name: string; slug: string; logo_url: string } | null;
  device: PosDevice | null;
  deviceToken: string | null;
  workers: ShiftWorker[];
  menu: PosMenuSnapshot | null;
  activeShift: CashShift | null;
  posSettings: PosSettings | null;
  currentWorker: ShiftWorker | null;
  incomingOrders: PosOrder[];
  tables: Array<{ id: number; name: string; table_number: number; public_token: string }>;

  cart: PosOrderItem[];
  cartNotes: string;
  fulfillmentType: string;
  selectedTableId: number | null;
  selectedCustomerId: number | null;

  recentOrders: PosOrder[];

  setMerchant: (m: { id: number; business_name: string; slug: string; logo_url: string }) => void;
  setDevice: (d: PosDevice, token: string) => void;
  setWorkers: (w: ShiftWorker[]) => void;
  setMenu: (m: PosMenuSnapshot) => void;
  setActiveShift: (s: CashShift | null) => void;
  setPosSettings: (s: PosSettings) => void;
  setCurrentWorker: (w: ShiftWorker | null) => void;
  setIncomingOrders: (orders: PosOrder[]) => void;

  addItemToCart: (item: PosOrderItem) => void;
  removeItemFromCart: (idx: number) => void;
  updateCartItemQty: (idx: number, qty: number) => void;
  clearCart: () => void;
  setCartNotes: (n: string) => void;
  setFulfillmentType: (t: string) => void;
  setSelectedTable: (id: number | null) => void;
  setSelectedCustomer: (id: number | null) => void;

  setRecentOrders: (orders: PosOrder[]) => void;

  bootstrap: (resp: PosBootstrapResponse) => void;
  reset: () => void;
}

const initialState = {
  merchant: null,
  device: null,
  deviceToken: null,
  workers: [],
  menu: null,
  activeShift: null,
  posSettings: null,
  currentWorker: null,
  incomingOrders: [],
  tables: [],
  cart: [],
  cartNotes: "",
  fulfillmentType: "dine-in",
  selectedTableId: null,
  selectedCustomerId: null,
  recentOrders: [],
};

export const usePosStore = create<PosState>((set) => ({
  ...initialState,

  setMerchant: (m) => set({ merchant: m }),
  setDevice: (d, token) => set({ device: d, deviceToken: token }),
  setWorkers: (w) => set({ workers: w }),
  setMenu: (m) => set({ menu: m }),
  setActiveShift: (s) => {
    if (s) {
      localStorage.setItem("pos_active_shift", JSON.stringify(s));
    } else {
      localStorage.removeItem("pos_active_shift");
    }
    set({ activeShift: s });
  },
  setPosSettings: (s) => set({ posSettings: s }),
  setCurrentWorker: (w) => {
    if (w) {
      localStorage.setItem("pos_worker_id", w.id);
      localStorage.setItem("pos_worker", JSON.stringify(w));
    } else {
      localStorage.removeItem("pos_worker_id");
      localStorage.removeItem("pos_worker");
    }
    set({ currentWorker: w });
  },
  setIncomingOrders: (orders) => set({ incomingOrders: orders }),

  addItemToCart: (item) =>
    set((state) => {
      const idx = state.cart.findIndex(
        (c) => c.menu_item_id === item.menu_item_id
      );
      if (idx >= 0) {
        const updated = [...state.cart];
        updated[idx] = {
          ...updated[idx],
          quantity: updated[idx].quantity + item.quantity,
          subtotal:
            (updated[idx].quantity + item.quantity) * updated[idx].price,
        };
        return { cart: updated };
      }
      return { cart: [...state.cart, item] };
    }),

  removeItemFromCart: (idx) =>
    set((state) => ({
      cart: state.cart.filter((_, i) => i !== idx),
    })),

  updateCartItemQty: (idx, qty) =>
    set((state) => {
      const updated = [...state.cart];
      updated[idx] = {
        ...updated[idx],
        quantity: qty,
        subtotal: qty * updated[idx].price,
      };
      return { cart: updated };
    }),

  clearCart: () => set({ cart: [], cartNotes: "", selectedTableId: null, selectedCustomerId: null }),
  setCartNotes: (n) => set({ cartNotes: n }),
  setFulfillmentType: (t) => set({ fulfillmentType: t }),
  setSelectedTable: (id) => set({ selectedTableId: id }),
  setSelectedCustomer: (id) => set({ selectedCustomerId: id }),

  setRecentOrders: (orders) => set({ recentOrders: orders }),

  bootstrap: (resp) => {
    // Restore worker from localStorage (validated against server data)
    const savedWorkerId = localStorage.getItem("pos_worker_id");
    const savedWorkerJson = localStorage.getItem("pos_worker");
    let restoredWorker: ShiftWorker | null = null;

    if (savedWorkerId && savedWorkerJson) {
      try {
        const parsed = JSON.parse(savedWorkerJson) as ShiftWorker;
        // Validate worker still exists and is active
        const serverWorker = resp.workers.find((w) => w.id === savedWorkerId && w.is_active);
        restoredWorker = serverWorker ?? null;
      } catch {
        restoredWorker = null;
      }
    }
    if (!restoredWorker) {
      localStorage.removeItem("pos_worker_id");
      localStorage.removeItem("pos_worker");
    }

    // Restore active shift from localStorage (validated against server)
    let restoredShift: CashShift | null = null;
    if (resp.active_shift) {
      restoredShift = resp.active_shift;
      localStorage.setItem("pos_active_shift", JSON.stringify(restoredShift));
    } else {
      // No active shift on server, clear any stale localStorage
      localStorage.removeItem("pos_active_shift");
    }

    set({
      merchant: resp.merchant,
      device: resp.device,
      deviceToken: null,
      workers: resp.workers,
      menu: resp.menu,
      activeShift: restoredShift,
      posSettings: resp.pos_settings,
      recentOrders: resp.recent_orders,
      incomingOrders: resp.incoming_orders || [],
      tables: resp.tables || [],
      currentWorker: restoredWorker,
    });
  },

  reset: () => {
    localStorage.removeItem("pos_worker_id");
    localStorage.removeItem("pos_worker");
    localStorage.removeItem("pos_active_shift");
    set(initialState);
  },
}));
