import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-[var(--radius-sm)] px-[0.5rem] py-[0.15rem] text-[var(--text-xs)] font-medium whitespace-nowrap transition-colors",
  {
    variants: {
      variant: {
        default: "bg-[var(--badge-default-bg)] text-[var(--badge-default-text)]",
        success: "bg-[var(--badge-success-bg)] text-[var(--badge-success-text)]",
        warning: "bg-[var(--badge-warning-bg)] text-[var(--badge-warning-text)]",
        danger: "bg-[var(--badge-danger-bg)] text-[var(--badge-danger-text)]",
        processing: "bg-[var(--badge-processing-bg)] text-[var(--badge-processing-text)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}
