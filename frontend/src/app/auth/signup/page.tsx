"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Mail, Lock, User, Phone, Eye, EyeOff, ChevronRight, ChevronLeft, Check, Loader2, Briefcase } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";

const step1Schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8).regex(/[A-Z]/, "Must have uppercase").regex(/[0-9]/, "Must have a digit"),
  confirmPassword: z.string(),
}).refine(d => d.password === d.confirmPassword, { message: "Passwords do not match", path: ["confirmPassword"] });

const step2Schema = z.object({
  first_name: z.string().min(1, "Required"),
  last_name: z.string().min(1, "Required"),
  phone: z.string().optional(),
});

const step3Schema = z.object({
  role: z.enum(["Employee", "Guard", "Manager"]),
});

type Step1 = z.infer<typeof step1Schema>;
type Step2 = z.infer<typeof step2Schema>;
type Step3 = z.infer<typeof step3Schema>;

const ROLES = [
  { value: "Employee", label: "Employee", desc: "Standard access to assigned lockers" },
  { value: "Guard", label: "Guard", desc: "Monitor and respond to security events" },
  { value: "Manager", label: "Manager", desc: "Manage lockers, users, and access control" },
];

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [showPass, setShowPass] = useState(false);
  const [formData, setFormData] = useState<Partial<Step1 & Step2 & Step3>>({});

  const f1 = useForm<Step1>({ resolver: zodResolver(step1Schema) });
  const f2 = useForm<Step2>({ resolver: zodResolver(step2Schema) });
  const f3 = useForm<Step3>({ resolver: zodResolver(step3Schema), defaultValues: { role: "Employee" } });

  const handleStep1 = (data: Step1) => { setFormData(p => ({ ...p, ...data })); setStep(2); };
  const handleStep2 = (data: Step2) => { setFormData(p => ({ ...p, ...data })); setStep(3); };

  const handleStep3 = async (data: Step3) => {
    const payload = { ...formData, ...data };
    try {
      await authApi.signup(payload);
      if (typeof window !== "undefined") localStorage.setItem("va_verify_email", payload.email!);
      toast.success("Account created! Check your email for a verification code.");
      router.push("/auth/verify");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Signup failed.";
      toast.error(msg);
    }
  };

  const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 60 : -60, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -60 : 60, opacity: 0 }),
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="relative w-full max-w-md">
        <div className="absolute -inset-px rounded-3xl bg-gradient-to-r from-vault-500/20 via-transparent to-purple-500/20 blur-2xl" />
        <div className="relative glass-card p-8">
          <div className="mb-6 flex flex-col items-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-vault-500/20 ring-1 ring-vault-500/30 mb-3">
              <Shield className="h-6 w-6 text-vault-400" />
            </div>
            <h1 className="text-xl font-bold text-slate-100">Create Account</h1>
            <p className="mt-1 text-sm text-slate-500">Join VaultAlert Security Platform</p>
          </div>

          {/* Step indicators */}
          <div className="flex items-center justify-center gap-2 mb-8">
            {[1, 2, 3].map(i => (
              <div key={i} className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold transition-all duration-300 ${step === i ? "bg-vault-500 text-white ring-4 ring-vault-500/20" : step > i ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30" : "bg-white/5 text-slate-500 ring-1 ring-white/10"}`}>
                {step > i ? <Check className="h-4 w-4" /> : i}
              </div>
            ))}
          </div>

          <AnimatePresence mode="wait" custom={1}>
            {step === 1 && (
              <motion.form key="step1" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.25 }} onSubmit={f1.handleSubmit(handleStep1)} className="space-y-4">
                <p className="section-title mb-4">Account Credentials</p>
                <div className="space-y-1.5">
                  <label className="stat-label">Email address</label>
                  <div className="relative"><Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" /><input {...f1.register("email")} type="email" placeholder="admin@company.com" className="vault-input pl-10" /></div>
                  {f1.formState.errors.email && <p className="text-xs text-red-400">{f1.formState.errors.email.message}</p>}
                </div>
                <div className="space-y-1.5">
                  <label className="stat-label">Password</label>
                  <div className="relative"><Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" /><input {...f1.register("password")} type={showPass ? "text" : "password"} placeholder="Min 8 chars, 1 uppercase, 1 digit" className="vault-input pl-10 pr-10" /><button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500">{showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div>
                  {f1.formState.errors.password && <p className="text-xs text-red-400">{f1.formState.errors.password.message}</p>}
                </div>
                <div className="space-y-1.5">
                  <label className="stat-label">Confirm Password</label>
                  <div className="relative"><Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" /><input {...f1.register("confirmPassword")} type={showPass ? "text" : "password"} placeholder="Repeat password" className="vault-input pl-10" /></div>
                  {f1.formState.errors.confirmPassword && <p className="text-xs text-red-400">{f1.formState.errors.confirmPassword.message}</p>}
                </div>
                <button type="submit" className="btn-primary w-full mt-2">Next <ChevronRight className="h-4 w-4" /></button>
              </motion.form>
            )}

            {step === 2 && (
              <motion.form key="step2" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.25 }} onSubmit={f2.handleSubmit(handleStep2)} className="space-y-4">
                <p className="section-title mb-4">Your Profile</p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="stat-label">First Name</label>
                    <div className="relative"><User className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" /><input {...f2.register("first_name")} placeholder="Alex" className="vault-input pl-10" /></div>
                    {f2.formState.errors.first_name && <p className="text-xs text-red-400">{f2.formState.errors.first_name.message}</p>}
                  </div>
                  <div className="space-y-1.5">
                    <label className="stat-label">Last Name</label>
                    <input {...f2.register("last_name")} placeholder="Johnson" className="vault-input" />
                    {f2.formState.errors.last_name && <p className="text-xs text-red-400">{f2.formState.errors.last_name.message}</p>}
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="stat-label">Phone (optional)</label>
                  <div className="relative"><Phone className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" /><input {...f2.register("phone")} placeholder="+1 555 000 0000" className="vault-input pl-10" /></div>
                </div>
                <div className="flex gap-2 mt-2">
                  <button type="button" onClick={() => setStep(1)} className="btn-ghost flex-1"><ChevronLeft className="h-4 w-4" /> Back</button>
                  <button type="submit" className="btn-primary flex-1">Next <ChevronRight className="h-4 w-4" /></button>
                </div>
              </motion.form>
            )}

            {step === 3 && (
              <motion.form key="step3" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.25 }} onSubmit={f3.handleSubmit(handleStep3)} className="space-y-4">
                <p className="section-title mb-4">Select Your Role</p>
                <div className="space-y-2">
                  {ROLES.map(r => (
                    <label key={r.value} className="flex items-start gap-3 cursor-pointer rounded-xl border border-white/8 bg-white/3 p-3.5 transition-all hover:border-vault-500/30 has-[:checked]:border-vault-500/40 has-[:checked]:bg-vault-500/8">
                      <input {...f3.register("role")} type="radio" value={r.value} className="mt-0.5 accent-vault-500" />
                      <div>
                        <p className="text-sm font-semibold text-slate-200">{r.label}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{r.desc}</p>
                      </div>
                    </label>
                  ))}
                </div>
                <div className="flex gap-2 mt-2">
                  <button type="button" onClick={() => setStep(2)} className="btn-ghost flex-1"><ChevronLeft className="h-4 w-4" /> Back</button>
                  <button type="submit" disabled={f3.formState.isSubmitting} className="btn-primary flex-1">{f3.formState.isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Shield className="h-4 w-4" />} {f3.formState.isSubmitting ? "Creating..." : "Create Account"}</button>
                </div>
              </motion.form>
            )}
          </AnimatePresence>

          <p className="mt-6 text-center text-xs text-slate-600">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-vault-400 hover:text-vault-300 transition-colors">Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}