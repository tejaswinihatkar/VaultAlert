"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Mail, ArrowLeft, Loader2, Send } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import Link from "next/link";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const forgotSchema = z.object({
  email: z.string().email("Enter a valid email"),
});

type ForgotForm = z.infer<typeof forgotSchema>;

export default function ForgotPasswordPage() {
  const [isSuccess, setIsSuccess] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<ForgotForm>({
    resolver: zodResolver(forgotSchema)
  });

  const onSubmit = async (data: ForgotForm) => {
    try {
      await authApi.forgotPassword({ email: data.email });
      if (typeof window !== "undefined") {
        localStorage.setItem("va_verify_email", data.email);
      }
      setIsSuccess(true);
      toast.success("Password reset code sent!");
    } catch (err: unknown) {
      toast.error("An error occurred. Please try again.");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="relative w-full max-w-sm">
        <div className="absolute -inset-px rounded-3xl bg-gradient-to-r from-vault-500/20 via-transparent to-purple-500/20 blur-2xl" />
        <div className="relative glass-card p-8">
          <div className="mb-6 flex flex-col items-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-vault-500/20 ring-1 ring-vault-500/30 mb-3">
              <Shield className="h-6 w-6 text-vault-400" />
            </div>
            <h1 className="text-xl font-bold text-slate-100">Reset Password</h1>
            <p className="mt-1 text-sm text-slate-500">Recover access to your VaultAlert account</p>
          </div>

          <AnimatePresence mode="wait">
            {!isSuccess ? (
              <motion.form
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onSubmit={handleSubmit(onSubmit)}
                className="space-y-4"
              >
                <div className="space-y-1.5">
                  <label className="stat-label">Email address</label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <input
                      {...register("email")}
                      type="email"
                      placeholder="admin@company.com"
                      className="vault-input pl-10"
                    />
                  </div>
                  {errors.email && <p className="text-xs text-red-400">{errors.email.message}</p>}
                </div>

                <button type="submit" disabled={isSubmitting} className="btn-primary w-full py-3">
                  {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  {isSubmitting ? "Sending..." : "Send Reset Code"}
                </button>
              </motion.form>
            ) : (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center py-4 space-y-4"
              >
                <p className="text-sm text-slate-300">
                  If this email is registered, we have sent a 6-digit security code to verify your request.
                </p>
                <Link href="/auth/verify" className="btn-primary w-full py-3 inline-flex items-center justify-center">
                  Verify Code
                </Link>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="mt-6 flex justify-center text-xs">
            <Link href="/auth/login" className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300 transition-colors">
              <ArrowLeft className="h-3 w-3" /> Back to Login
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
}