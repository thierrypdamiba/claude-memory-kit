"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import {
  ArrowRight,
  ArrowUpRight,
  Brain,
  Shield,
  Database,
  Github,
  Twitter,
  Menu,
  X,
} from "lucide-react";
import Image from "next/image";
import { cn } from "@/lib/utils";

/* ─── Animated Background ─── */
function HeroBackground() {
  const interactiveRef = useRef<HTMLDivElement>(null);
  const curX = useRef(0);
  const curY = useRef(0);
  const tgX = useRef(0);
  const tgY = useRef(0);

  useEffect(() => {
    let frame: number;
    function animate() {
      if (interactiveRef.current) {
        curX.current += (tgX.current - curX.current) / 20;
        curY.current += (tgY.current - curY.current) / 20;
        interactiveRef.current.style.transform = `translate(${Math.round(curX.current)}px, ${Math.round(curY.current)}px)`;
      }
      frame = requestAnimationFrame(animate);
    }
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden">
      {/* Static blobs matching logo palette */}
      <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-[radial-gradient(circle,_rgba(59,130,246,0.15)_0%,_transparent_70%)]" />
      <div className="absolute top-[10%] right-[-10%] w-[50%] h-[50%] bg-[radial-gradient(circle,_rgba(245,101,37,0.12)_0%,_transparent_70%)]" />
      <div className="absolute bottom-[-10%] left-[20%] w-[50%] h-[50%] bg-[radial-gradient(circle,_rgba(16,185,129,0.12)_0%,_transparent_70%)]" />
      <div className="absolute bottom-[10%] right-[10%] w-[40%] h-[40%] bg-[radial-gradient(circle,_rgba(234,179,8,0.1)_0%,_transparent_70%)]" />

      {/* Interactive blob */}
      <div
        ref={interactiveRef}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          tgX.current = e.clientX - rect.left - rect.width / 2;
          tgY.current = e.clientY - rect.top - rect.height / 2;
        }}
        className="absolute w-[40%] h-[40%] top-[30%] left-[30%] bg-[radial-gradient(circle,_rgba(168,85,247,0.12)_0%,_transparent_60%)] pointer-events-auto"
      />
    </div>
  );
}

/* ─── Project Card ─── */
interface ProjectCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  gradient: string;
  tags: string[];
  href: string;
  index: number;
}

function ProjectCard({ title, description, icon, gradient, tags, href, index }: ProjectCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const [rotation, setRotation] = useState({ x: 0, y: 0 });

  return (
    <motion.a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.12 }}
    >
      <motion.div
        ref={cardRef}
        className="relative rounded-2xl overflow-hidden bg-[#0a0a0a] border border-white/[0.08] cursor-pointer"
        style={{ transformStyle: "preserve-3d", height: "360px" }}
        animate={{
          y: isHovered ? -6 : 0,
          rotateX: rotation.x,
          rotateY: rotation.y,
        }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => {
          setIsHovered(false);
          setRotation({ x: 0, y: 0 });
        }}
        onMouseMove={(e) => {
          if (cardRef.current) {
            const rect = cardRef.current.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            setRotation({ x: -(y / rect.height) * 4, y: (x / rect.width) * 4 });
          }
        }}
      >
        {/* Glow */}
        <motion.div
          className="absolute bottom-0 left-0 right-0 h-2/3 z-0"
          style={{ background: gradient, filter: "blur(50px)" }}
          animate={{ opacity: isHovered ? 0.9 : 0.6 }}
        />

        {/* Bottom edge glow */}
        <motion.div
          className="absolute bottom-0 left-0 right-0 h-[2px] z-10"
          style={{ background: gradient.replace("blur", "") }}
          animate={{
            opacity: isHovered ? 1 : 0.5,
          }}
        />

        {/* Content */}
        <div className="relative flex flex-col h-full p-8 z-20">
          <motion.div
            className="w-12 h-12 rounded-xl flex items-center justify-center mb-6 bg-white/[0.06] border border-white/[0.08]"
            animate={{
              scale: isHovered ? 1.05 : 1,
            }}
          >
            {icon}
          </motion.div>

          <div className="mb-auto">
            <h3 className="text-2xl font-semibold text-white mb-3">{title}</h3>
            <p className="text-sm text-gray-400 leading-relaxed mb-6">
              {description}
            </p>
            <div className="flex flex-wrap gap-2 mb-6">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] tracking-wider uppercase px-2.5 py-1 rounded-full bg-white/[0.06] text-gray-500 border border-white/[0.06]"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center text-white text-sm font-medium">
            View Project
            <motion.span animate={{ x: isHovered ? 4 : 0 }}>
              <ArrowUpRight className="ml-1 w-4 h-4" />
            </motion.span>
          </div>
        </div>
      </motion.div>
    </motion.a>
  );
}

/* ─── Main Page ─── */
export default function Home() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();
  const heroOpacity = useTransform(scrollY, [0, 500], [1, 0.4]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const projects: Omit<ProjectCardProps, "index">[] = [
    {
      title: "CMK",
      description:
        "Claude Memory Kit. Persistent memory layer that intercepts conversations via MCP, classifies memories through five semantic gates, and enables recall across sessions. Local-first with optional cloud sync to Qdrant.",
      icon: <Database className="h-5 w-5 text-blue-400" />,
      gradient:
        "linear-gradient(135deg, rgba(59,130,246,0.6) 0%, rgba(16,185,129,0.3) 100%)",
      tags: ["Rust", "MCP", "SQLite", "Qdrant", "Next.js"],
      href: "https://github.com/thierrypdamiba/cmk",
    },
    {
      title: "Onboard",
      description:
        "Personalized codebase onboarding powered by Opus. Ingests full repository context and generates role-specific documentation. An SRE sees production risks. A new grad sees learning paths. Adapts in real-time.",
      icon: <Brain className="h-5 w-5 text-amber-400" />,
      gradient:
        "linear-gradient(135deg, rgba(234,179,8,0.6) 0%, rgba(245,101,37,0.3) 100%)",
      tags: ["Rust", "Axum", "Claude API", "Git2", "Streaming"],
      href: "https://github.com/thierrypdamiba/onboard",
    },
    {
      title: "Airlock",
      description:
        "Preflight security analysis for pull requests. A GitHub App that scores risk, enforces policies, and blocks dangerous changes before they land. Fail-closed architecture with emergency bypass and full audit trail.",
      icon: <Shield className="h-5 w-5 text-red-400" />,
      gradient:
        "linear-gradient(135deg, rgba(239,68,68,0.6) 0%, rgba(168,85,247,0.3) 100%)",
      tags: ["Rust", "Axum", "GitHub API", "PostgreSQL", "Claude API"],
      href: "https://github.com/thierrypdamiba/airlock",
    },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* ── Header ── */}
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.5 }}
        className={cn(
          "sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-xl transition-shadow",
          scrolled && "shadow-sm"
        )}
      >
        <div className="mx-auto flex h-18 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Image src="/logo.png" alt="Amoeba Labs" width={44} height={44} className="h-11 w-11" />
            <Image src="/wordmark.png" alt="Amoeba Labs" width={180} height={36} className="h-8 w-auto" />
          </div>

          <nav className="hidden md:flex items-center gap-8">
            <a href="#projects" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Projects
            </a>
            <a href="#thesis" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Thesis
            </a>
            <a href="#approach" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Approach
            </a>
          </nav>

          <div className="hidden md:flex items-center gap-4">
            <a
              href="https://github.com/thierrypdamiba"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <Github className="h-5 w-5" />
            </a>
            <a
              href="https://x.com/thaborelli"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <Twitter className="h-5 w-5" />
            </a>
          </div>

          <button className="md:hidden" onClick={() => setIsMenuOpen(!isMenuOpen)}>
            {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </motion.header>

      {/* Mobile menu */}
      {isMenuOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 bg-background md:hidden"
        >
          <div className="flex h-16 items-center justify-between px-6">
            <Image src="/wordmark.png" alt="Amoeba Labs" width={140} height={28} className="h-6 w-auto" />
            <button onClick={() => setIsMenuOpen(false)}>
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="grid gap-2 px-6 pt-4">
            {["Projects", "Thesis", "Approach"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="rounded-lg px-4 py-3 text-lg font-medium hover:bg-accent"
                onClick={() => setIsMenuOpen(false)}
              >
                {item}
              </a>
            ))}
            <div className="flex gap-4 mt-4 px-4">
              <a href="https://github.com/thierrypdamiba" target="_blank" rel="noopener noreferrer" className="text-muted-foreground">
                <Github className="h-5 w-5" />
              </a>
              <a href="https://x.com/thaborelli" target="_blank" rel="noopener noreferrer" className="text-muted-foreground">
                <Twitter className="h-5 w-5" />
              </a>
            </div>
          </nav>
        </motion.div>
      )}

      <main className="flex-1">
        {/* ── Hero ── */}
        <section className="relative w-full min-h-[90vh] flex items-center justify-center overflow-hidden">
          <HeroBackground />
          <motion.div style={{ opacity: heroOpacity }} className="relative z-10 mx-auto max-w-4xl px-6 text-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="inline-flex items-center gap-2 rounded-full bg-muted px-4 py-1.5 text-sm border border-border mb-8"
            >
              <div className="h-2 w-2 rounded-full bg-gradient-to-r from-blue-500 to-emerald-500 animate-pulse" />
              Research Lab
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[0.95]"
            >
              How far can
              <br />
              one person go{" "}
              <span className="bg-gradient-to-r from-blue-500 via-emerald-500 via-amber-500 via-orange-500 to-red-500 bg-clip-text text-transparent">
                with AI?
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.3 }}
              className="mt-8 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed"
            >
              Amoeba Labs builds tools for people who ship alone.
              One person should be able to do what used to take a team.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.45 }}
              className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <a
                href="#projects"
                className="inline-flex items-center gap-2 rounded-full bg-foreground text-background px-6 py-3 text-sm font-medium hover:bg-foreground/90 transition-colors"
              >
                View Projects
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="https://github.com/thierrypdamiba"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-border px-6 py-3 text-sm font-medium hover:bg-accent transition-colors"
              >
                <Github className="h-4 w-4" />
                GitHub
              </a>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.7, delay: 0.6 }}
              className="mt-16 flex items-center justify-center gap-8 text-xs text-muted-foreground"
            >
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                3 projects shipped
              </div>
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                1 human
              </div>
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                0 employees
              </div>
            </motion.div>
          </motion.div>
        </section>

        {/* ── Projects ── */}
        <section id="projects" className="w-full py-24 md:py-32">
          <div className="mx-auto max-w-6xl px-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="text-center mb-16"
            >
              <div className="inline-flex items-center rounded-full bg-muted px-4 py-1.5 text-sm border border-border mb-6">
                Our Work
              </div>
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight">
                Projects
              </h2>
              <p className="mt-4 text-lg text-muted-foreground max-w-xl mx-auto">
                Real software, built solo. Rust backends, real databases, paying users.
              </p>
            </motion.div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {projects.map((project, i) => (
                <ProjectCard key={project.title} {...project} index={i} />
              ))}
            </div>
          </div>
        </section>

        {/* ── Thesis ── */}
        <section id="thesis" className="w-full py-24 md:py-32 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/[0.03] via-emerald-500/[0.03] to-orange-500/[0.03]" />
          <div className="mx-auto max-w-6xl px-6 relative z-10">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7 }}
              >
                <div className="inline-flex items-center rounded-full bg-muted px-4 py-1.5 text-sm border border-border mb-8">
                  Thesis
                </div>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight mb-8">
                  The best software will be built by{" "}
                  <span className="bg-gradient-to-r from-blue-500 via-emerald-500 to-amber-500 bg-clip-text text-transparent">
                    tiny teams
                  </span>
                </h2>
                <p className="text-lg text-muted-foreground leading-relaxed mb-6">
                  AI changes what one person can build. The bottleneck used to be
                  headcount. Now it is taste, speed, and willingness to ship.
                </p>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Every project here was built by one person. Not demos, not prototypes.
                  These are real products with real users. Amoeba Labs exists to see how
                  far that can go.
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7 }}
                className="relative h-[360px] rounded-3xl overflow-hidden border border-border bg-gradient-to-br from-muted/50 to-muted/20 flex items-center justify-center"
              >
                <motion.div
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                >
                  <Image
                    src="/logo.png"
                    alt="Amoeba Labs"
                    width={240}
                    height={240}
                    className="w-52 h-52 object-contain"
                  />
                </motion.div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* ── Approach ── */}
        <section id="approach" className="w-full py-24 md:py-32">
          <div className="mx-auto max-w-6xl px-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="text-center mb-16"
            >
              <div className="inline-flex items-center rounded-full bg-muted px-4 py-1.5 text-sm border border-border mb-6">
                How We Work
              </div>
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight">
                Approach
              </h2>
            </motion.div>

            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  num: "01",
                  title: "Build real things",
                  description:
                    "No toy demos. Every project has auth, billing, and deployment. Rust backends, real databases, paying users.",
                  color: "text-blue-500",
                },
                {
                  num: "02",
                  title: "Stay small",
                  description:
                    "More people means more coordination, not more output. Working solo forces you to pick better tools and simpler architecture. Zero meetings, zero overhead.",
                  color: "text-emerald-500",
                },
                {
                  num: "03",
                  title: "Ship constantly",
                  description:
                    "When you own the whole stack, the feedback loop shrinks to minutes. No PRs to review, no deploys to schedule. Just push and see what happens.",
                  color: "text-amber-500",
                },
              ].map((item, i) => (
                <motion.div
                  key={item.num}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                  className="rounded-2xl border border-border p-8 hover:border-border/80 hover:bg-accent/50 transition-all"
                >
                  <div className={cn("text-sm font-mono font-bold mb-4", item.color)}>
                    {item.num}
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{item.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {item.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="w-full border-t bg-background">
        <div className="mx-auto max-w-6xl px-6 py-12">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="flex items-center gap-2.5">
              <Image src="/logo.png" alt="Amoeba Labs" width={32} height={32} className="h-8 w-8" />
              <Image src="/wordmark.png" alt="Amoeba Labs" width={120} height={24} className="h-5 w-auto" />
            </div>
            <div className="flex items-center gap-6">
              <a
                href="https://github.com/thierrypdamiba"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                GitHub
              </a>
              <a
                href="https://x.com/thaborelli"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                X
              </a>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-sm text-muted-foreground">
            <span>&copy; {new Date().getFullYear()} Amoeba Labs</span>
            <div className="flex items-center gap-4">
              <a href="/privacy" className="hover:text-foreground transition-colors">
                Privacy Policy
              </a>
              <a href="/terms" className="hover:text-foreground transition-colors">
                Terms of Service
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
