interface LogoProps { size?: 'sm' | 'md' | 'lg' }

export default function Logo({ size = 'md' }: LogoProps) {
  const cls = {
    sm: 'text-lg tracking-widest',
    md: 'text-2xl tracking-widest',
    lg: 'text-4xl tracking-widest',
  }[size]

  return (
    <span className={`font-display font-black ${cls} select-none`}>
      <span className="text-gradient">PROMPT</span>
      <span className="text-white">X</span>
      <span className="text-neon-violet ml-2">PRELIMS</span>
    </span>
  )
}
