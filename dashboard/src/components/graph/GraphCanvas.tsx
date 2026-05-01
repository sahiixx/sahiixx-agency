import { useRef, useEffect, useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import * as d3 from 'd3'
import {
  CATEGORY_COLORS,
  ERA_COLORS,
  EDGE_STYLES,
  nodeRadius,
  type RepoNode,
  type LinkData,
} from '@/lib/graph-data'

interface GraphCanvasProps {
  nodes: RepoNode[]
  links: LinkData[]
  viewMode: 'category' | 'layer' | 'era'
  selectedRepo: RepoNode | null
  hoveredRepo: string | null
  onHover: (id: string | null) => void
  onClick: (repo: RepoNode) => void
  activePattern: string | null
  patternNodes: Set<string>
}

export default function GraphCanvas({
  nodes,
  links,
  viewMode,
  selectedRepo,
  hoveredRepo,
  onHover,
  onClick,
  activePattern,
  patternNodes,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const gRef = useRef<SVGGElement | null>(null)
  const simulationRef = useRef<d3.Simulation<d3.SimulationNodeDatum, undefined> | null>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const [miniMapOpen, setMiniMapOpen] = useState(false)

  // Measure container
  useEffect(() => {
    function measure() {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      setDimensions({ width: rect.width, height: rect.height })
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])

  // Initialize D3 simulation
  useEffect(() => {
    if (!svgRef.current || dimensions.width === 0 || dimensions.height === 0) return
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const width = dimensions.width
    const height = dimensions.height

    const g = svg.append('g')
    gRef.current = g.node()

    // Background ambient glow
    svg
      .append('defs')
      .append('radialGradient')
      .attr('id', 'ambient-glow')
      .attr('cx', '50%')
      .attr('cy', '-20%')
      .attr('r', '80%')
      .selectAll('stop')
      .data([
        { offset: '0%', color: 'rgba(139,92,246,0.06)' },
        { offset: '100%', color: 'transparent' },
      ])
      .join('stop')
      .attr('offset', (d) => d.offset)
      .attr('stop-color', (d) => d.color)

    g.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'url(#ambient-glow)')

    // Edge particle defs
    const defs = svg.append('defs')
    Object.entries(EDGE_STYLES).forEach(([type, style]) => {
      const grad = defs.append('linearGradient').attr('id', `edge-grad-${type}`)
      grad.append('stop').attr('offset', '0%').attr('stop-color', style.color).attr('stop-opacity', 0)
      grad.append('stop').attr('offset', '50%').attr('stop-color', style.color).attr('stop-opacity', 0.6)
      grad.append('stop').attr('offset', '100%').attr('stop-color', style.color).attr('stop-opacity', 0)
    })

    // Prepare simulation nodes with mutable x/y
    const simNodes: (RepoNode & d3.SimulationNodeDatum)[] = nodes.map((n) => ({
      ...n,
      x: width / 2 + (Math.random() - 0.5) * 200,
      y: height / 2 + (Math.random() - 0.5) * 200,
    }))

    const nodeById = new Map(simNodes.map((n) => [n.id, n]))

    const simLinks = links.map((l) => ({
      ...l,
      source: nodeById.get(typeof l.source === 'string' ? l.source : l.source.id) || l.source,
      target: nodeById.get(typeof l.target === 'string' ? l.target : l.target.id) || l.target,
    })) as d3.SimulationLinkDatum<d3.SimulationNodeDatum>[] & LinkData[]

    // Force simulation
    const simulation = d3
      .forceSimulation(simNodes as d3.SimulationNodeDatum[])
      .force(
        'link',
        d3
          .forceLink(simLinks)
          .id((d: any) => d.id)
          .distance(80)
          .strength((d: any) => d.strength * 0.3)
      )
      .force('charge', d3.forceManyBody().strength(-300).distanceMax(400))
      .force('collide', d3.forceCollide((d: any) => nodeRadius(d.stars) + 8))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('gravity', d3.forceY(height / 2).strength(0.05))
      .alphaDecay(0.02)

    simulationRef.current = simulation

    // Apply view mode constraints
    if (viewMode === 'layer') {
      const layers = ['Compute', 'Model', 'Framework', 'Agent', 'Tool', 'Application', 'Data', 'Interface']
      simulation.force('center', null)
      simulation.force('gravity', null)
      simulation.force(
        'y',
        d3.forceY((d: any) => {
          const idx = layers.indexOf(d.layer)
          const frac = idx >= 0 ? (idx + 0.5) / layers.length : 0.5
          return height * (1 - frac * 0.7 + 0.15)
        }).strength(0.8)
      )
    } else if (viewMode === 'era') {
      const eras = ['landmark', 'recent', 'trending']
      simulation.force('center', null)
      simulation.force('gravity', null)
      simulation.force(
        'x',
        d3.forceX((d: any) => {
          const idx = eras.indexOf(d.era)
          if (idx === 0) return width * 0.2
          if (idx === 1) return width * 0.5
          return width * 0.8
        }).strength(0.8)
      )
    } else {
      simulation.force('y', null)
      simulation.force('x', null)
      simulation.force('center', d3.forceCenter(width / 2, height / 2))
      simulation.force('gravity', d3.forceY(height / 2).strength(0.05))
    }

    // Edge groups
    const linkGroup = g.append('g').attr('class', 'links')
    const linkSel = linkGroup
      .selectAll('line')
      .data(simLinks)
      .join('line')
      .attr('stroke', (d: any) => EDGE_STYLES[d.type]?.color || '#94a3b8')
      .attr('stroke-width', (d: any) => d.strength * 0.8)
      .attr('stroke-opacity', 0.3)
      .attr('stroke-dasharray', (d: any) => EDGE_STYLES[d.type]?.dash || '0')

    // Animated particles along edges
    const particleGroup = g.append('g').attr('class', 'particles')
    const particles = particleGroup
      .selectAll('circle')
      .data(simLinks)
      .join('circle')
      .attr('r', 2)
      .attr('fill', (d: any) => EDGE_STYLES[d.type]?.color || '#94a3b8')
      .attr('opacity', 0.8)

    // Node groups
    const nodeGroup = g.append('g').attr('class', 'nodes')
    const nodeSel = nodeGroup
      .selectAll('g')
      .data(simNodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(
        d3.drag<any, any>()
          .on('start', (event, d: any) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event, d: any) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event, d: any) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          }) as any
      )

    // Node circles
    nodeSel
      .append('circle')
      .attr('class', 'node-circle')
      .attr('r', (d: any) => nodeRadius(d.stars))
      .attr('fill', (d: any) => {
        const c = CATEGORY_COLORS[d.category]?.fill || '#94a3b8'
        return `${c}33`
      })
      .attr('stroke', (d: any) => CATEGORY_COLORS[d.category]?.fill || '#94a3b8')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.4)
      .attr('filter', (d: any) => {
        const glow = CATEGORY_COLORS[d.category]?.glow || 'rgba(148,163,184,0.4)'
        // Use inline drop-shadow for glow
        return `drop-shadow(0 0 8px ${glow})`
      })

    // Era indicator dot
    nodeSel
      .append('circle')
      .attr('class', 'era-dot')
      .attr('r', 3)
      .attr('cx', (d: any) => nodeRadius(d.stars) * 0.6)
      .attr('cy', (d: any) => -nodeRadius(d.stars) * 0.6)
      .attr('fill', (d: any) => ERA_COLORS[d.era] || '#94a3b8')
      .attr('stroke', '#050508')
      .attr('stroke-width', 1)

    // Labels
    nodeGroup
      .selectAll('text')
      .data(simNodes)
      .join('text')
      .attr('class', 'node-label')
      .text((d: any) => d.name)
      .attr('font-size', 12)
      .attr('font-family', 'Inter, sans-serif')
      .attr('font-weight', 500)
      .attr('fill', '#f1f5f9')
      .attr('text-anchor', 'middle')
      .attr('dy', (d: any) => nodeRadius(d.stars) + 14)
      .attr('pointer-events', 'none')
      .attr('opacity', 0)

    // Hover / click interactions
    nodeSel
      .on('mouseenter', (_event, d: any) => {
        onHover(d.id)
      })
      .on('mouseleave', () => {
        onHover(null)
      })
      .on('click', (_event, d: any) => {
        onClick(d)
      })

    // Tick function
    let t = 0
    simulation.on('tick', () => {
      t += 1
      linkSel
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y)

      nodeSel.attr('transform', (d: any) => `translate(${d.x},${d.y})`)

      // Animate particles along edges
      particles.attr('transform', (d: any) => {
        const progress = ((t * 0.005 * (d.strength || 1)) % 1)
        const x = d.source.x + (d.target.x - d.source.x) * progress
        const y = d.source.y + (d.target.y - d.source.y) * progress
        return `translate(${x},${y})`
      })
    })

    // Zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform.toString())
      })

    zoomRef.current = zoom
    svg.call(zoom as any)

    // Initial zoom to fit
    const bounds = svg.node()?.getBBox?.()
    if (bounds && bounds.width > 0 && bounds.height > 0) {
      const fullWidth = bounds.width
      const fullHeight = bounds.height
      const midX = bounds.x + fullWidth / 2
      const midY = bounds.y + fullHeight / 2
      const scale = Math.min(
        width / fullWidth,
        height / fullHeight,
        1.5
      ) * 0.9
      svg.call(
        zoom.transform as any,
        d3.zoomIdentity.translate(width / 2, height / 2).scale(scale).translate(-midX, -midY)
      )
    }

    return () => {
      simulation.stop()
    }
  }, [nodes, links, dimensions, viewMode, onHover, onClick])

  // Update visual states based on hover/selection/pattern
  useEffect(() => {
    if (!gRef.current) return
    const g = d3.select(gRef.current)

    const hoveredSet = new Set<string>()
    if (hoveredRepo) {
      hoveredSet.add(hoveredRepo)
      links.forEach((l) => {
        const s = typeof l.source === 'string' ? l.source : l.source.id
        const t = typeof l.target === 'string' ? l.target : l.target.id
        if (s === hoveredRepo) hoveredSet.add(t)
        if (t === hoveredRepo) hoveredSet.add(s)
      })
    }

    g.selectAll('.nodes g').each(function (d: any) {
      const isHovered = d.id === hoveredRepo
      const isConnected = hoveredSet.has(d.id)
      const isDimmed = hoveredRepo && !isHovered && !isConnected
      const isPatternDimmed = activePattern && !patternNodes.has(d.id)

      const circle = d3.select(this).select('.node-circle')
      const label = d3.select(this).select('.node-label')

      const targetOpacity = isPatternDimmed ? 0.2 : isDimmed ? 0.4 : 1
      const targetScale = isHovered ? 1.3 : 1

      circle
        .transition()
        .duration(200)
        .attr('opacity', targetOpacity)
        .attr('transform', `scale(${targetScale})`)

      label
        .transition()
        .duration(200)
        .attr('opacity', isHovered || isConnected ? 1 : 0)
    })

    g.selectAll('.links line').each(function (d: any) {
      const s = typeof d.source === 'string' ? d.source : d.source.id
      const t = typeof d.target === 'string' ? d.target : d.target.id
      const isConnected = hoveredRepo && (s === hoveredRepo || t === hoveredRepo)
      d3.select(this)
        .transition()
        .duration(200)
        .attr('stroke-opacity', isConnected ? 0.9 : 0.3)
        .attr('stroke-width', isConnected ? (d.strength * 0.8 + 1) : d.strength * 0.8)
    })
  }, [hoveredRepo, links, activePattern, patternNodes])

  // Center on selected repo
  useEffect(() => {
    if (!selectedRepo || !svgRef.current || !zoomRef.current) return
    const svg = d3.select(svgRef.current)
    const g = d3.select(gRef.current)
    const node = g.selectAll('.nodes g').filter((d: any) => d.id === selectedRepo.id)
    if (node.empty()) return
    const d = node.datum() as any
    const width = dimensions.width
    const height = dimensions.height
    svg
      .transition()
      .duration(400)
      .call(
        zoomRef.current.transform as any,
        d3.zoomIdentity.translate(width / 2, height / 2).scale(1.5).translate(-d.x, -d.y)
      )
  }, [selectedRepo, dimensions])

  const handleZoomIn = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoomRef.current.scaleBy as any, 1.3)
  }, [])

  const handleZoomOut = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoomRef.current.scaleBy as any, 1 / 1.3)
  }, [])

  const handleZoomReset = useCallback(() => {
    if (!svgRef.current || !zoomRef.current || dimensions.width === 0) return
    const svg = d3.select(svgRef.current)
    svg
      .transition()
      .duration(300)
      .call(zoomRef.current.transform as any, d3.zoomIdentity)
  }, [dimensions])

  return (
    <div ref={containerRef} className="absolute inset-0 overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      {/* Noise overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.05]"
        style={{
          backgroundImage: 'url(/hero-bg-noise.png)',
          backgroundRepeat: 'repeat',
        }}
      />

      <svg ref={svgRef} className="w-full h-full" />

      {/* Zoom controls */}
      <div className="fixed bottom-4 right-4 z-30 flex flex-col gap-2">
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.1 }}
          onClick={handleZoomIn}
          className="glass-tag w-9 h-9 flex items-center justify-center hover:scale-110 transition-transform"
        >
          <span className="text-text-primary font-bold text-[14px]">+</span>
        </motion.button>
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          onClick={handleZoomReset}
          className="glass-tag w-9 h-9 flex items-center justify-center hover:scale-110 transition-transform"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-text-primary">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
        </motion.button>
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.3 }}
          onClick={handleZoomOut}
          className="glass-tag w-9 h-9 flex items-center justify-center hover:scale-110 transition-transform"
        >
          <span className="text-text-primary font-bold text-[14px]">−</span>
        </motion.button>
      </div>

      {/* Mini-map toggle */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.0 }}
        onClick={() => setMiniMapOpen((v) => !v)}
        className="fixed bottom-4 right-16 z-30 glass-tag w-9 h-9 flex items-center justify-center hover:scale-110 transition-transform lg:flex hidden"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-text-primary">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
      </motion.button>

      {/* Mini-map */}
      {miniMapOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed bottom-16 right-4 z-30 glass-panel rounded-[10px] w-[180px] h-[120px] overflow-hidden hidden lg:block"
        >
          <svg width="180" height="120" className="w-full h-full">
            {nodes.map((n) => (
              <circle
                key={n.id}
                cx={((Math.random() * 0.8 + 0.1) * 180)}
                cy={((Math.random() * 0.8 + 0.1) * 120)}
                r={2}
                fill={CATEGORY_COLORS[n.category]?.fill || '#94a3b8'}
                opacity={0.6}
              />
            ))}
            <rect
              x="20"
              y="15"
              width="140"
              height="90"
              fill="none"
              stroke="var(--accent-cyan)"
              strokeWidth="1"
              strokeDasharray="2 2"
              opacity="0.5"
            />
          </svg>
        </motion.div>
      )}
    </div>
  )
}
