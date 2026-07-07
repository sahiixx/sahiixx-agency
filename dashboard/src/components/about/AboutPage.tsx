import { motion } from 'framer-motion'
import { Cpu, Users, Zap, Shield, Github, Twitter, Linkedin } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

const features = [
  {
    icon: Cpu,
    title: 'AI-Powered',
    description: 'Leveraging cutting-edge machine learning to deliver intelligent insights.',
    bgClass: 'bg-accent-cyan/10',
    textClass: 'text-accent-cyan',
  },
  {
    icon: Zap,
    title: 'Lightning Fast',
    description: 'Optimized performance for real-time data processing and visualization.',
    bgClass: 'bg-accent-amber/10',
    textClass: 'text-accent-amber',
  },
  {
    icon: Shield,
    title: 'Secure by Design',
    description: 'Enterprise-grade security with end-to-end encryption and privacy controls.',
    bgClass: 'bg-accent-green/10',
    textClass: 'text-accent-green',
  },
  {
    icon: Users,
    title: 'Team Collaboration',
    description: 'Built for teams to work together seamlessly across projects.',
    bgClass: 'bg-accent-purple/10',
    textClass: 'text-accent-purple',
  },
]

const socials = [
  { icon: Github, label: 'GitHub', href: 'https://github.com' },
  { icon: Twitter, label: 'Twitter', href: 'https://twitter.com' },
  { icon: Linkedin, label: 'LinkedIn', href: 'https://linkedin.com' },
]

export function AboutPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="min-h-[100dvh] px-4 py-8 md:px-8"
    >
      <div className="max-w-4xl mx-auto">
        {/* Hero */}
        <div className="text-center mb-16">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="inline-block mb-6"
          >
            <div className="rounded-2xl bg-accent-cyan/10 p-4">
              <Cpu className="h-12 w-12 text-accent-cyan" />
            </div>
          </motion.div>
          <h1 className="font-display text-4xl md:text-5xl font-bold text-text-primary mb-4">
            One Person Agency
          </h1>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto">
            A unified command center for orchestrating AI tools, repos, and agents.
            Dispatch intents, monitor tasks, and run workflows across your entire agency.
          </p>
        </div>

        {/* Features */}
        <div className="grid sm:grid-cols-2 gap-4 mb-16">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
            >
              <Card className="h-full">
                <CardContent className="pt-6">
                  <div className={`rounded-lg ${feature.bgClass} p-3 w-fit mb-4`}>
                    <feature.icon className={`h-5 w-5 ${feature.textClass}`} />
                  </div>
                  <h3 className="font-display font-semibold text-text-primary mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-text-secondary">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Mission */}
        <Card className="mb-16">
          <CardHeader>
            <CardTitle className="font-display">Our Mission</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-text-secondary">
            <p>
              One Person Agency was built to give a single operator control over an army of AI
              tools and repos. It auto-discovers modules, routes natural-language intents,
              executes them safely, and remembers context across tasks.
            </p>
            <p>
              The dashboard aggregates your agency registry, task stream, approval queue, and
              discovery feed into one interface you can use through the web, CLI, Telegram, or MCP.
            </p>
          </CardContent>
        </Card>

        {/* Tech Stack */}
        <Card className="mb-16">
          <CardHeader>
            <CardTitle className="font-display">Built With</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              {['React 19', 'TypeScript', 'Tailwind CSS', 'Vite'].map((tech) => (
                <div
                  key={tech}
                  className="rounded-lg border border-border bg-muted/50 px-4 py-3"
                >
                  <span className="text-sm font-medium text-text-primary">{tech}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Social */}
        <div className="text-center">
          <Separator className="mb-8" />
          <p className="text-text-muted mb-4">Connect with us</p>
          <div className="flex justify-center gap-4">
            {socials.map((social) => (
              <Button
                key={social.label}
                variant="outline"
                size="icon"
                asChild
              >
                <a
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => {
                    e.preventDefault()
                    toast.info(`${social.label}`, {
                      description: `Opening ${social.label}...`,
                    })
                    window.open(social.href, '_blank', 'noopener,noreferrer')
                  }}
                >
                  <social.icon className="h-4 w-4" />
                </a>
              </Button>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
