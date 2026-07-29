"use client";
import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Shield, CheckCircle2, RefreshCw, Mail, ArrowLeft, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import Link from "next/link";

export default function VerifyPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState<string[]>(Array(6).fill(""));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const inputRefs = useRef<HTMLInputElement[]>([]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedEmail = localStorage.getItem("va_verify_email") || "";
      setEmail(storedEmail);
    }
  }, []);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleChange = (element: HTMLInputElement, index: number) => {
    const value = element.value;
    if (isNaN(Number(value))) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Focus next
    if (value !== "" && index < 5) {
      inputRefs.current[index + 1].focus();
    }

    // Auto submit
    if (newOtp.every(val => val !== "")) {
      handleSubmit(newOtp.join(""));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === "Backspace" && otp[index] === "" && index > 0) {
      inputRefs.current[index - 1].focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").trim();
    if (pastedData.length !== 6 || isNaN(Number(pastedData))) return;

    const newOtp = pastedData.split("");
    setOtp(newOtp);
    handleSubmit(pastedData);
  };

  const handleSubmit = async (code: string) => {
    setIsSubmitting(true);
    try {
      await authApi.verifyOtp({ email, otp_code: code });
      toast.success("Account verified successfully! You can now log in.");
      localStorage.removeItem("va_verify_email");
      router.push("/auth/login");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Verification failed.";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    try {
      await authApi.forgotPassword({ email }); // triggers OTP resend using standard mechanism
      toast.success("Verification code resent to your email.");
      setResendCooldown(60);
    } catch (err: unknown) {
      toast.error("Failed to resend code.");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="relative w-full max-w-md">
        <div className="absolute -inset-px rounded-3xl bg-gradient-to-r from-vault-500/20 via-transparent to-purple-500/20 blur-2xl" />
        <div className="relative glass-card p-8 text-center">
          <div className="mb-6 flex flex-col items-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-vault-500/20 ring-1 ring-vault-500/30 mb-3">
              <Shield className="h-6 w-6 text-vault-400" />
            </div>
            <h1 className="text-xl font-bold text-slate-100">Verify Email</h1>
            <p className="mt-1 text-sm text-slate-500">Enter the 6-digit code sent to your email</p>
            <p className="text-xs text-vault-300 font-medium mt-1">{email}</p>
          </div>

          <div className="flex justify-center gap-2 mb-8" onPaste={handlePaste}>
            {otp.map((data, index) => (
              <input
                key={index}
                type="text"
                maxLength={1}
                value={data}
                onChange={e => handleChange(e.target, index)}
                onKeyDown={e => handleKeyDown(e, index)}
                ref={el => { if (el) inputRefs.current[index] = el; }}
                className="w-12 h-14 rounded-xl border border-white/10 bg-white/4 text-center text-xl font-bold text-slate-100 outline-none transition-all focus:border-vault-500/50 focus:ring-2 focus:ring-vault-500/20"
              />
            ))}
          </div>

          <button
            onClick={() => handleSubmit(otp.join(""))}
            disabled={isSubmitting || otp.some(v => v === "")}
            className="btn-primary w-full py-3 mb-4"
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            {isSubmitting ? "Verifying..." : "Verify Code"}
          </button>

          <div className="flex justify-between items-center text-xs">
            <Link href="/auth/login" className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300 transition-colors">
              <ArrowLeft className="h-3 w-3" /> Back to Login
            </Link>
            <button
              onClick={handleResend}
              disabled={resendCooldown > 0}
              className="flex items-center gap-1.5 text-vault-400 hover:text-vault-300 transition-colors disabled:opacity-50"
            >
              <RefreshCw className="h-3 w-3" />
              {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : "Resend Code"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}