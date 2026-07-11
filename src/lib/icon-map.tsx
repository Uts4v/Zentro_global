import {
  Coffee,
  Gift,
  Target,
  PartyPopper,
  Sparkles,
  Bell,
  CheckCircle,
  XCircle,
  FileText,
  Flame,
  UtensilsCrossed,
  Leaf,
  ClipboardList,
  Inbox,
  Ticket,
  ShoppingBag,
  MapPin,
  Trophy,
  Medal,
  Sun,
  Moon,
  Search,
  Star,
  Check,
  type LucideIcon,
} from "lucide-react";

const emojiToIconMap: Record<string, LucideIcon> = {
  "\u2615": Coffee,
  "\uD83C\uDF81": Gift,
  "\uD83C\uDFAF": Target,
  "\uD83C\uDF89": PartyPopper,
  "\u2728": Sparkles,
  "\uD83D\uDD14": Bell,
  "\u2705": CheckCircle,
  "\u274C": XCircle,
  "\uD83E\uDDFE": FileText,
  "\uD83D\uDD25": Flame,
  "\uD83C\uDF7D\uFE0F": UtensilsCrossed,
  "\uD83C\uDF75": Leaf,
  "\uD83D\uDCCB": ClipboardList,
  "\uD83D\uDCE9": Inbox,
  "\uD83C\uDF9F\uFE0F": Ticket,
  "\uD83D\uDECD\uFE0F": ShoppingBag,
  "\uD83D\uDCCD": MapPin,
  "\uD83E\uDD47": Trophy,
  "\uD83E\uDD48": Medal,
  "\uD83E\uDD49": Medal,
  "\u2600\uFE0F": Sun,
  "\uD83C\uDF19": Moon,
  "\uD83D\uDD0D": Search,
  "\u2605": Star,
  "\u2713": Check,
  "\u2714": Check,
  "\u2726": Sparkles,
  "\uD83C\uDF7D": UtensilsCrossed,
  "\uD83E\uDED8": Coffee,
};

export function emojiToIcon(emoji: string): LucideIcon | null {
  return emojiToIconMap[emoji] ?? null;
}

export function renderEmojiIcon(emoji: string, className = "h-5 w-5"): React.ReactNode {
  const Icon = emojiToIcon(emoji);
  if (Icon) return <Icon className={className} />;
  return <span className="text-lg">{emoji}</span>;
}
