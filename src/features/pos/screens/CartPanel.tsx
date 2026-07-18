import { usePosStore } from "../store";
import { useState } from "react";
import { PosReceiptData, PosCustomer } from "../api";
import CustomerSearchModal from "./CustomerSearchModal";
import {
  Minus,
  Plus,
  Trash2,
  MessageSquare,
  ShoppingBag,
  Percent,
  CreditCard,
  FileText,
  UserPlus,
  User,
  Hash,
} from "lucide-react";

interface CartPanelProps {
  onCheckout: () => void;
  onDiscount: () => void;
}

export default function CartPanel({ onCheckout, onDiscount }: CartPanelProps) {
  const cart = usePosStore((s) => s.cart);
  const cartNotes = usePosStore((s) => s.cartNotes);
  const fulfillmentType = usePosStore((s) => s.fulfillmentType);
  const posSettings = usePosStore((s) => s.posSettings);
  const merchant = usePosStore((s) => s.merchant);
  const currentWorker = usePosStore((s) => s.currentWorker);
  const tables = usePosStore((s) => s.tables);
  const selectedTableId = usePosStore((s) => s.selectedTableId);
  const updateCartItemQty = usePosStore((s) => s.updateCartItemQty);
  const removeItemFromCart = usePosStore((s) => s.removeItemFromCart);
  const clearCart = usePosStore((s) => s.clearCart);
  const setCartNotes = usePosStore((s) => s.setCartNotes);
  const setFulfillmentType = usePosStore((s) => s.setFulfillmentType);
  const setSelectedTable = usePosStore((s) => s.setSelectedTable);
  const setSelectedCustomer = usePosStore((s) => s.setSelectedCustomer);

  const [showNotes, setShowNotes] = useState(false);
  const [printingBill, setPrintingBill] = useState(false);
  const [showCustomerSearch, setShowCustomerSearch] = useState(false);
  const [linkedCustomer, setLinkedCustomer] = useState<PosCustomer | null>(null);

  const subtotal = cart.reduce((sum, item) => sum + item.subtotal, 0);
  const taxRate = 0.06; // 6% SST
  const tax = subtotal * taxRate;
  const total = subtotal + tax;
  const selectedTable = tables.find((t) => t.id === selectedTableId);

  const isEmpty = cart.length === 0;

  function handlePrintBill() {
    if (isEmpty) return;
    setPrintingBill(true);

    // Build a bill receipt from cart data
    const billData: PosReceiptData = {
      type: "bill",
      order_id: 0,
      order_uuid: "",
      order_number: "DRAFT",
      kot_number: null,
      status: "pending",
      source: "pos",
      created_at: new Date().toISOString(),
      client_created_at: null,
      merchant: {
        id: 0,
        name: merchant?.business_name ?? "ZENTRO",
        address: "",
        phone: "",
        logo_url: merchant?.logo_url ?? "",
      },
      table: selectedTable ? { name: selectedTable.name, number: selectedTable.table_number } : null,
      fulfillment_type: fulfillmentType,
      customer_name: null,
      worker_name: currentWorker?.display_name ?? null,
      items: cart.map((item) => ({
        name: item.name,
        price: String(item.price),
        quantity: item.quantity,
        subtotal: String(item.subtotal),
      })),
      subtotal: String(subtotal),
      discounts: [],
      discount_amount: "0.00",
      tax_amount: String(tax),
      service_charge: "0.00",
      total_amount: String(total),
      payments: [],
      total_paid: "0.00",
      change: "0.00",
      payment_status: "unpaid",
      payment_method: "",
      is_offline_receipt: false,
      sync_status: "synced",
    };

    // Open print window with bill content
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      setPrintingBill(false);
      return;
    }

    const receiptHtml = `
      <div style="font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.35; width: 72mm; padding: 4mm; color: #000; background: #fff;">
        <div style="text-align: center; margin-bottom: 8px;">
          <p style="font-size: 16px; font-weight: bold; margin: 0;">${billData.merchant.name}</p>
          <p style="font-size: 10px; color: #666; margin: 2px 0;">** DRAFT BILL **</p>
        </div>
        <hr style="border: none; border-top: 1px dashed #000; margin: 6px 0;">
        <div style="font-size: 11px;">
          <div style="display: flex; justify-content: space-between;"><span>Date</span><span>${new Date().toLocaleString("en-MY")}</span></div>
          <div style="display: flex; justify-content: space-between;"><span>Type</span><span>${billData.fulfillment_type}</span></div>
          ${billData.table ? `<div style="display: flex; justify-content: space-between;"><span>Table</span><span>${billData.table.name || "#" + billData.table.number}</span></div>` : ""}
          ${billData.worker_name ? `<div style="display: flex; justify-content: space-between;"><span>Served by</span><span>${billData.worker_name}</span></div>` : ""}
        </div>
        <hr style="border: none; border-top: 2px solid #000; margin: 8px 0;">
        <div style="font-size: 11px;">
          ${billData.items.map(item => `
            <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
              <span style="font-weight: bold;">${item.quantity}x ${item.name}</span>
              <span>Rs ${Number(item.subtotal).toFixed(2)}</span>
            </div>
            ${item.quantity > 1 ? `<div style="text-align: right; font-size: 10px; color: #666;">@ Rs ${Number(item.price).toFixed(2)} each</div>` : ""}
          `).join("")}
        </div>
        <hr style="border: none; border-top: 1px dashed #000; margin: 6px 0;">
        <div style="font-size: 11px;">
          <div style="display: flex; justify-content: space-between;"><span>Subtotal</span><span>Rs ${subtotal.toFixed(2)}</span></div>
          <div style="display: flex; justify-content: space-between;"><span>SST (6%)</span><span>Rs ${tax.toFixed(2)}</span></div>
          <hr style="border: none; border-top: 2px solid #000; margin: 6px 0;">
          <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 14px;">
            <span>TOTAL</span><span>Rs ${total.toFixed(2)}</span>
          </div>
        </div>
        <hr style="border: none; border-top: 1px dashed #000; margin: 8px 0;">
        <div style="text-align: center; font-size: 11px; font-weight: bold;">** AWAITING PAYMENT **</div>
      </div>
    `;

    printWindow.document.write(`
      <!DOCTYPE html>
      <html><head><title>Bill - ${billData.merchant.name}</title>
      <style>
        @page { size: 80mm auto; margin: 3mm; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { width: 72mm; }
        @media print {
          html, body { width: 72mm; }
          .no-print { display: none !important; }
        }
      </style>
      </head><body>
        <div class="no-print" style="padding: 8px; text-align: center; border-bottom: 1px solid #ccc; margin-bottom: 8px;">
          <button onclick="window.print(); window.close();" style="padding: 8px 16px; font-size: 14px; cursor: pointer; background: #1a1a1a; color: white; border: none; border-radius: 8px;">Print Bill</button>
        </div>
        ${receiptHtml}
      </body></html>
    `);
    printWindow.document.close();
    setPrintingBill(false);
  }

  return (
    <div className="flex h-full flex-col border-l border-border bg-background">
      {/* ── Header ── */}
      <div className="shrink-0 border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingBag className="h-4 w-4 text-ink" />
            <h2 className="text-sm font-bold text-foreground">Current Order</h2>
            {!isEmpty && (
              <span className="rounded-full bg-ink/10 px-2 py-0.5 text-[10px] font-bold text-ink">
                {cart.length} items
              </span>
            )}
          </div>
          {!isEmpty && (
            <button
              onClick={clearCart}
              className="text-xs text-destructive hover:underline"
            >
              Clear
            </button>
          )}
        </div>

        {/* Fulfillment type */}
        <div className="mt-3 flex gap-1.5">
          {["dine-in", "takeaway", "delivery"].map((type) => (
            <button
              key={type}
              onClick={() => {
                setFulfillmentType(type);
                if (type !== "dine-in") setSelectedTable(null);
              }}
              className={`flex-1 rounded-lg py-1.5 text-[11px] font-medium capitalize transition-colors ${
                fulfillmentType === type
                  ? "bg-ink text-white"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        {/* Table selector for dine-in */}
        {fulfillmentType === "dine-in" && tables.length > 0 && (
          <div className="mt-2">
            <div className="flex items-center gap-2 mb-1.5">
              <Hash className="h-3 w-3 text-muted-foreground" />
              <span className="text-[11px] font-medium text-muted-foreground">Table</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {tables.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelectedTable(selectedTableId === t.id ? null : t.id)}
                  className={`rounded-lg px-3 py-1.5 text-[11px] font-medium transition-colors ${
                    selectedTableId === t.id
                      ? "bg-ink text-white"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {t.name || `#${t.table_number}`}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Customer link */}
        <div className="mt-3">
          {linkedCustomer ? (
            <div className="flex items-center justify-between rounded-xl bg-ink/5 px-3 py-2">
              <div className="flex items-center gap-2">
                <User className="h-3.5 w-3.5 text-ink" />
                <div>
                  <p className="text-xs font-medium text-foreground">{linkedCustomer.full_name}</p>
                  <p className="text-[10px] text-muted-foreground">{linkedCustomer.tier} &middot; {linkedCustomer.loyalty_points} pts</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setLinkedCustomer(null);
                  setSelectedCustomer(null);
                }}
                className="text-[10px] text-destructive hover:underline"
              >
                Remove
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowCustomerSearch(true)}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-border py-2 text-xs text-muted-foreground hover:bg-muted"
            >
              <UserPlus className="h-3.5 w-3.5" />
              Link Customer
            </button>
          )}
        </div>
      </div>

      {/* Customer Search Modal */}
      {showCustomerSearch && (
        <CustomerSearchModal
          onSelect={(customer) => {
            setLinkedCustomer(customer);
            setSelectedCustomer(customer.id);
            setShowCustomerSearch(false);
          }}
          onClose={() => setShowCustomerSearch(false)}
        />
      )}

      {/* ── Cart items ── */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <ShoppingBag className="mb-3 h-10 w-10 opacity-30" />
            <p className="text-sm">Cart is empty</p>
            <p className="mt-1 text-xs">Tap items on the menu to add</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {cart.map((item, idx) => (
              <div key={`${item.menu_item_id}-${idx}`} className="px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {item.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Rs {item.price.toFixed(2)} each
                    </p>
                  </div>
                  <p className="text-sm font-bold text-ink">
                    Rs {item.subtotal.toFixed(2)}
                  </p>
                </div>

                {/* Quantity controls */}
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex items-center rounded-lg border border-border">
                    <button
                      onClick={() =>
                        item.quantity > 1
                          ? updateCartItemQty(idx, item.quantity - 1)
                          : removeItemFromCart(idx)
                      }
                      className="grid h-7 w-7 place-items-center text-muted-foreground hover:text-foreground"
                    >
                      {item.quantity === 1 ? (
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      ) : (
                        <Minus className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <span className="w-8 text-center text-sm font-medium">
                      {item.quantity}
                    </span>
                    <button
                      onClick={() => updateCartItemQty(idx, item.quantity + 1)}
                      className="grid h-7 w-7 place-items-center text-muted-foreground hover:text-foreground"
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Notes ── */}
      {!isEmpty && (
        <div className="shrink-0 border-t border-border px-4 py-2">
          <button
            onClick={() => setShowNotes(!showNotes)}
            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            {showNotes ? "Hide notes" : "Add notes"}
          </button>
          {showNotes && (
            <textarea
              value={cartNotes}
              onChange={(e) => setCartNotes(e.target.value)}
              placeholder="Special instructions..."
              rows={2}
              className="mt-2 w-full rounded-lg border border-border bg-muted/50 px-3 py-2 text-xs placeholder:text-muted-foreground focus:border-ink focus:outline-none focus:ring-1 focus:ring-ink"
            />
          )}
        </div>
      )}

      {/* ── Totals ── */}
      <div className="shrink-0 border-t border-border bg-muted/30 px-4 py-3 space-y-1.5">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Subtotal</span>
          <span>Rs {subtotal.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>SST (6%)</span>
          <span>Rs {tax.toFixed(2)}</span>
        </div>
        <div className="flex justify-between border-t border-border pt-1.5 text-sm font-bold text-foreground">
          <span>Total</span>
          <span>Rs {total.toFixed(2)}</span>
        </div>
      </div>

      {/* ── Actions ── */}
      <div className="shrink-0 space-y-2 border-t border-border px-4 py-3">
        {!isEmpty && posSettings?.receipt_printing_enabled && (
          <button
            onClick={handlePrintBill}
            disabled={printingBill}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-background py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted"
          >
            <FileText className="h-4 w-4" />
            {printingBill ? "Printing..." : "Print Bill"}
          </button>
        )}
        {posSettings?.discounts_enabled && (
          <button
            onClick={onDiscount}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-background py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted"
          >
            <Percent className="h-4 w-4" />
            Apply Discount
          </button>
        )}
        <button
          onClick={onCheckout}
          disabled={isEmpty}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-bold text-white transition-colors hover:opacity-90 disabled:opacity-40"
        >
          <CreditCard className="h-4 w-4" />
          {isEmpty
            ? "Cart is empty"
            : fulfillmentType === "dine-in"
              ? `Place Order — Rs ${total.toFixed(2)}`
              : `Pay Rs ${total.toFixed(2)}`}
        </button>
      </div>
    </div>
  );
}
