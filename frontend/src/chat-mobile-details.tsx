import type { RefObject } from "react";
import { ClipboardList, UserRound } from "lucide-react";

export type ChatDetailsSection = "customer" | "draft";

export function revealChatDetails(
  panel: RefObject<HTMLElement | null>,
  section: ChatDetailsSection,
) {
  requestAnimationFrame(() => {
    const node = panel.current;
    if (!node) return;
    node
      .querySelector<HTMLButtonElement>("header button")
      ?.focus({ preventScroll: true });
    if (section === "draft")
      node
        .querySelector(".order-draft-card, .ig-draft-card")
        ?.scrollIntoView({ block: "start" });
    else node.scrollTop = 0;
  });
}

export function ChatMobileDetails({
  open,
  canDraft,
}: {
  open: (section: ChatDetailsSection) => void;
  canDraft: boolean;
}) {
  return (
    <div
      className="chat-mobile-details"
      role="group"
      aria-label="Клиент и черновик"
    >
      <button type="button" onClick={() => open("customer")}>
        <UserRound size={16} />
        <span>Клиент и заказы</span>
      </button>
      <button
        type="button"
        disabled={!canDraft}
        title={
          canDraft
            ? "Открыть черновик заказа в боковой панели"
            : "Сначала свяжите диалог с клиентом"
        }
        onClick={() => open("draft")}
      >
        <ClipboardList size={16} />
        <span>Черновик заказа</span>
      </button>
    </div>
  );
}
