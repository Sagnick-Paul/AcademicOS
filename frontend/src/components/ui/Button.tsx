"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", fullWidth, className, type = "button", ...rest }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(styles.button, styles[variant], fullWidth && styles.fullWidth, className)}
      {...rest}
    />
  ),
);

Button.displayName = "Button";
