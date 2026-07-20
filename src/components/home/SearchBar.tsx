// src/components/home/SearchBar.tsx
// Rounded search bar with trailing filter button
import { Search, X as XIcon, SlidersHorizontal } from "lucide-react";

interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  merchantName?: string;
}

export function SearchBar({ value, onChange, placeholder, merchantName }: SearchBarProps) {
  return (
    <div className="relative">
      <Search className="absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-[#1A1A1A]/30" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || (merchantName ? `Search anything at ${merchantName}...` : "Search anything...")}
        className="h-12 w-full rounded-2xl bg-[#F5F3EF] pl-11 pr-20 text-[13px] text-[#1A1A1A] placeholder:text-[#1A1A1A]/30 focus:outline-none focus:ring-2 focus:ring-[#1A1A1A]/10 transition-shadow"
      />
      <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
        {value && (
          <button
            onClick={() => onChange("")}
            className="grid h-8 w-8 place-items-center rounded-xl text-[#1A1A1A]/40 hover:text-[#1A1A1A]/60 transition-colors"
          >
            <XIcon className="h-4 w-4" />
          </button>
        )}
        <button
          className="grid h-8 w-8 place-items-center rounded-xl bg-[#1A1A1A]/5 text-[#1A1A1A]/40 hover:bg-[#1A1A1A]/10 transition-colors"
          aria-label="Filter"
        >
          <SlidersHorizontal className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
