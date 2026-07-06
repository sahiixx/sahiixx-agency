import { useState } from 'react'
import { motion } from 'framer-motion'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Send, CheckCircle2, Mail, MapPin, Clock, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { contactSchema, type ContactFormData } from '@/lib/contact-schemas'

export function ContactPage() {
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)

  const form = useForm<ContactFormData>({
    resolver: zodResolver(contactSchema),
    defaultValues: { name: '', email: '', subject: '', message: '' },
  })

  const handleSubmit = form.handleSubmit(async (data) => {
    setLoading(true)

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))

    console.log('Contact form submitted:', data)
    toast.success('Message sent!', {
      description: `Thanks ${data.name}, we'll get back to you soon.`,
    })
    setLoading(false)
    setSubmitted(true)
    form.reset()
  })

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="min-h-[100dvh] px-4 py-8 md:px-8 flex items-center justify-center"
      >
        <Card className="max-w-md w-full text-center">
          <CardContent className="pt-10 pb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              className="mb-6 rounded-full bg-accent-green/10 p-4 inline-flex"
            >
              <CheckCircle2 className="h-10 w-10 text-accent-green" />
            </motion.div>
            <h2 className="font-display text-2xl font-bold text-text-primary mb-2">
              Message Sent!
            </h2>
            <p className="text-text-secondary mb-6">
              Thanks for reaching out. We'll get back to you within 24 hours.
            </p>
            <Button onClick={() => setSubmitted(false)}>
              Send Another Message
            </Button>
          </CardContent>
        </Card>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="min-h-[100dvh] px-4 py-8 md:px-8"
    >
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold text-text-primary mb-1">
            Contact
          </h1>
          <p className="text-text-secondary">
            Get in touch with us
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {/* Info Cards */}
          <div className="space-y-4">
            <Card>
              <CardContent className="flex items-center gap-4 pt-6">
                <div className="rounded-lg bg-accent-cyan/10 p-3">
                  <Mail className="h-5 w-5 text-accent-cyan" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">Email</p>
                  <p className="text-sm text-text-secondary">hello@ainexus.dev</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-4 pt-6">
                <div className="rounded-lg bg-accent-purple/10 p-3">
                  <MapPin className="h-5 w-5 text-accent-purple" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">Location</p>
                  <p className="text-sm text-text-secondary">San Francisco, CA</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-4 pt-6">
                <div className="rounded-lg bg-accent-green/10 p-3">
                  <Clock className="h-5 w-5 text-accent-green" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">Response Time</p>
                  <p className="text-sm text-text-secondary">Within 24 hours</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Contact Form */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="font-display">Send a Message</CardTitle>
              <CardDescription>
                Fill out the form below and we'll get back to you as soon as possible.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-text-primary">Name</label>
                    <Input
                      {...form.register('name')}
                      placeholder="Your name"
                      disabled={loading}
                    />
                    {form.formState.errors.name && (
                      <p className="text-xs text-destructive">
                        {form.formState.errors.name.message}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-text-primary">Email</label>
                    <Input
                      {...form.register('email')}
                      type="email"
                      placeholder="you@example.com"
                      disabled={loading}
                    />
                    {form.formState.errors.email && (
                      <p className="text-xs text-destructive">
                        {form.formState.errors.email.message}
                      </p>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-text-primary">Subject</label>
                  <Input
                    {...form.register('subject')}
                    placeholder="What's this about?"
                    disabled={loading}
                  />
                  {form.formState.errors.subject && (
                    <p className="text-xs text-destructive">
                      {form.formState.errors.subject.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-text-primary">Message</label>
                  <Textarea
                    {...form.register('message')}
                    placeholder="Tell us more..."
                    rows={5}
                    disabled={loading}
                  />
                  {form.formState.errors.message && (
                    <p className="text-xs text-destructive">
                      {form.formState.errors.message.message}
                    </p>
                  )}
                </div>

                <Button type="submit" className="w-full gap-2" disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      Send Message
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  )
}
