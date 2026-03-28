<template>
  <div class="h-full flex flex-col relative overflow-hidden group/graph">
    <!-- Graph Header -->
    <div class="h-12 flex items-center justify-between px-4 border-b border-white/5 bg-white/5 backdrop-blur-md z-10">
      <div class="flex items-center gap-2">
        <NetworkIcon class="w-4 h-4 text-pitchy-cyan shadow-glow shadow-pitchy-cyan" />
        <span class="text-[10px] font-bold text-white/60 uppercase tracking-widest">Архитектура общества</span>
      </div>

      <div class="flex items-center gap-2">
        <div class="flex items-center gap-4 mr-4 text-[10px] font-mono text-white/30 uppercase tracking-tighter">
          <span v-if="graphData">{{ graphData.node_count || 0 }} Nodes</span>
          <span v-if="graphData" class="w-px h-2 bg-white/10"></span>
          <span v-if="graphData">{{ graphData.edge_count || 0 }} Edges</span>
        </div>
        <button 
          @click="$emit('refresh')" 
          :disabled="loading" 
          class="p-1.5 hover:bg-white/10 rounded-lg transition-all text-white/40 hover:text-pitchy-cyan disabled:opacity-30"
          title="Sync with Neo4j"
        >
          <RefreshCwIcon class="w-4 h-4" :class="{ 'animate-spin': loading }" />
        </button>
      </div>
    </div>
    
    <div class="flex-1 relative" ref="graphContainer">
      <!-- D3 SVG Layer -->
      <svg ref="graphSvg" class="w-full h-full cursor-move bg-pitchy-bg/20"></svg>
      
      <!-- Overlays -->
      <div v-if="currentPhase === 1 || isSimulating" class="absolute bottom-4 right-4 z-10 animate-in fade-in slide-in-from-bottom-2 duration-500">
        <StatusBadge type="cyan" class="shadow-glow-cyan bg-[#0A0A0F]/80 backdrop-blur-xl border-white/10 transition-all">
          {{ isSimulating ? 'GraphRAG Real-time Memory Pulse' : 'Constructing Reality Threads' }}
        </StatusBadge>
      </div>

      <!-- Hint box redesigned as a slide-in alert -->
      <Transition name="slide-up">
        <div v-if="showSimulationFinishedHint" class="absolute top-16 left-1/2 -translate-x-1/2 z-20 w-full max-w-md px-4">
          <div class="glass-card p-4 flex items-center justify-between border-pitchy-cyan/30 bg-pitchy-cyan/5">
            <div class="flex items-center gap-3">
              <InfoIcon class="w-5 h-5 text-pitchy-cyan" />
              <span class="text-xs text-white/80 leading-snug">Simulation complete. Manual sync recommended to capture final state items.</span>
            </div>
            <button @click="dismissFinishedHint" class="p-1 hover:text-white transition-colors text-white/40">
              <XIcon class="w-4 h-4" />
            </button>
          </div>
        </div>
      </Transition>
      
      <!-- Detail Panel Redesigned -->
      <Transition name="slide-left">
        <div v-if="selectedItem" class="absolute top-4 right-4 bottom-4 w-80 z-30">
          <GlassCard class="h-full flex flex-col p-0 shadow-2xl border-white/10 bg-[#0A0A0F]/90">
            <div class="p-4 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
              <div class="space-y-1">
                <span class="text-[9px] font-bold text-white/30 uppercase tracking-[0.2em]">{{ selectedItem.type === 'node' ? 'Entity Record' : 'Relationship Instance' }}</span>
                <div class="flex items-center gap-2">
                  <h4 class="text-sm font-bold text-white truncate max-w-[140px]">
                    {{ selectedItem.type === 'node' ? selectedItem.data.name : selectedItem.data.name || 'Relation' }}
                  </h4>
                  <StatusBadge v-if="selectedItem.type === 'node'" type="default" :dot="false" class="scale-75 origin-left">
                    {{ translateType(selectedItem.entityType) }}
                  </StatusBadge>
                </div>
              </div>
              <button @click="closeDetailPanel" class="p-1.5 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
                <XIcon class="w-4 h-4" />
              </button>
            </div>

            <div class="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
              <!-- Meta Info -->
              <div class="space-y-4">
                <div class="space-y-1">
                  <span class="text-[9px] font-mono text-white/20 uppercase">UUID Reference</span>
                  <div class="text-[10px] font-mono text-white/40 break-all bg-white/5 p-2 rounded-lg border border-white/5">
                    {{ selectedItem.data.uuid }}
                  </div>
                </div>

                <div v-if="selectedItem.data.summary" class="space-y-1">
                  <span class="text-[9px] font-bold text-white/30 uppercase tracking-widest">Abstract</span>
                  <p class="text-xs text-white/60 leading-relaxed italic">"{{ selectedItem.data.summary }}"</p>
                </div>

                <!-- Properties Grid -->
                <div v-if="selectedItem.data.attributes && Object.keys(selectedItem.data.attributes).length" class="space-y-2">
                  <span class="text-[9px] font-bold text-white/30 uppercase tracking-widest">Matrix Properties</span>
                  <div class="grid grid-cols-1 gap-2">
                    <div v-for="(v, k) in selectedItem.data.attributes" :key="k" class="p-2 rounded-lg bg-white/[0.02] border border-white/5 flex items-start justify-between gap-4">
                      <span class="text-[10px] text-white/30 font-mono">{{ k }}</span>
                      <span class="text-[10px] text-white/70 text-right truncate max-w-[120px]">{{ v || '-' }}</span>
                    </div>
                  </div>
                </div>

                <!-- Labels/Tags -->
                <div v-if="selectedItem.data.labels?.length" class="flex flex-wrap gap-2 pt-2">
                  <span v-for="l in selectedItem.data.labels" :key="l" class="px-2 py-0.5 rounded bg-white/5 text-[9px] font-mono text-white/40 border border-white/5">
                    #{{ l }}
                  </span>
                </div>
              </div>

              <!-- Relation Specific (Edges) -->
              <div v-if="selectedItem.type === 'edge' && !selectedItem.data.isSelfLoopGroup" class="space-y-4 pt-4 border-t border-white/5">
                <div class="flex items-center justify-center gap-3 py-4 bg-white/[0.01] rounded-xl border border-dashed border-white/5">
                  <div class="text-[10px] text-white/50 font-bold truncate max-w-[80px]">{{ selectedItem.data.source_name }}</div>
                  <ChevronRightIcon class="w-3 h-3 text-pitchy-violet" />
                  <div class="text-[10px] text-white px-2 py-1 bg-white/5 rounded-md border border-white/10 font-mono">{{ selectedItem.data.name }}</div>
                  <ChevronRightIcon class="w-3 h-3 text-pitchy-cyan" />
                  <div class="text-[10px] text-white/50 font-bold truncate max-w-[80px]">{{ selectedItem.data.target_name }}</div>
                </div>
                
                <div v-if="selectedItem.data.fact" class="space-y-1">
                   <span class="text-[9px] font-bold text-white/30 uppercase tracking-widest">Observed Fact</span>
                   <p class="text-[11px] text-white/70 leading-relaxed p-3 bg-white/[0.02] rounded-xl border border-white/10 italic">
                     {{ selectedItem.data.fact }}
                   </p>
                </div>
              </div>

              <!-- Self-Loop Group -->
              <div v-if="selectedItem.data.isSelfLoopGroup" class="space-y-3">
                <span class="text-[9px] font-bold text-white/30 uppercase tracking-widest">Recurrent Links ({{ selectedItem.data.selfLoopCount }})</span>
                <div class="space-y-2">
                  <div v-for="(loop, idx) in selectedItem.data.selfLoopEdges" :key="loop.uuid || idx" class="p-3 rounded-xl bg-white/5 border border-white/5 space-y-2">
                    <div class="flex items-center justify-between">
                      <span class="text-[10px] font-bold text-pitchy-violet">LINK_{{ idx+1 }}</span>
                      <span class="text-[9px] font-mono text-white/20">{{ loop.fact_type || 'REL' }}</span>
                    </div>
                    <p class="text-[10px] text-white/60 leading-relaxed italic">"{{ loop.fact }}"</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="p-3 border-t border-white/5 text-[9px] text-white/20 font-mono text-center">
              SYNC_STATE: 100%_SECURE_LOCAL
            </div>
          </GlassCard>
        </div>
      </Transition>
    </div>

    <!-- Bottom Legnd & Controls -->
    <div v-if="graphData && entityTypes.length" class="absolute bottom-4 left-4 z-10 flex items-end gap-4 pointer-events-none">
      <div class="glass-card p-3 rounded-xl border-white/5 pointer-events-auto">
        <div class="text-[8px] font-bold text-white/30 uppercase tracking-[0.2em] mb-3">Легенда онтологии</div>
        <div class="flex flex-wrap items-center gap-x-4 gap-y-2 max-w-sm">
          <div v-for="t in entityTypes" :key="t.name" class="flex items-center gap-2 group/legend">
            <div class="w-2 h-2 rounded-full shadow-glow" :style="{ background: t.color, '--tw-shadow-color': t.color }"></div>
            <span class="text-[9px] font-bold text-white/50 group-hover/legend:text-white transition-colors">{{ translateType(t.name) }}</span>
          </div>
        </div>
      </div>

      <div class="glass-card p-1.5 px-3 rounded-xl border-white/5 pointer-events-auto flex items-center gap-3">
        <span class="text-[9px] font-bold text-white/30 uppercase tracking-widest">Show Labels</span>
        <label class="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" v-model="showEdgeLabels" class="sr-only peer" />
          <div class="w-7 h-4 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-pitchy-violet"></div>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as d3 from 'd3'
import GlassCard from './ui/GlassCard.vue'
import StatusBadge from './ui/StatusBadge.vue'
import { 
  Network as NetworkIcon, 
  RefreshCw as RefreshCwIcon, 
  X as XIcon,
  Info as InfoIcon,
  ChevronRight as ChevronRightIcon
} from 'lucide-vue-next'

const props = defineProps({
  graphData: Object,
  loading: Boolean,
  currentPhase: Number,
  isSimulating: Boolean
})

const emit = defineEmits(['refresh', 'toggle-maximize'])

const graphContainer = ref(null)
const graphSvg = ref(null)
const selectedItem = ref(null)
const showEdgeLabels = ref(true)
const expandedSelfLoops = ref(new Set())
const showSimulationFinishedHint = ref(false)
const wasSimulating = ref(false)

// Colors based on Pitchy Palette
const pitchyColors = [
  '#8B5CF6', // Violet
  '#06B6D4', // Cyan
  '#10B981', // Emerald
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#6366F1', // Indigo
  '#EC4899', // Pink
  '#F97316', // Orange
]

const LABEL_MAP = {
  'Organization': 'Организация',
  'Entity': 'Сущность',
  'Person': 'Человек',
  'StartupFounder': 'Фаундер',
  'MarketplaceSeller': 'Селлер'
}

const translateType = (type) => LABEL_MAP[type] || type

const dismissFinishedHint = () => { showSimulationFinishedHint.value = false }

watch(() => props.isSimulating, (nv, ov) => {
  if (wasSimulating.value && !nv) showSimulationFinishedHint.value = true
  wasSimulating.value = nv
}, { immediate: true })

const entityTypes = computed(() => {
  if (!props.graphData?.nodes) return []
  const typeMap = {}
  props.graphData.nodes.forEach(node => {
    const type = node.labels?.find(l => l !== 'Entity') || 'Entity'
    if (!typeMap[type]) {
      typeMap[type] = { name: type, count: 0, color: pitchyColors[Object.keys(typeMap).length % pitchyColors.length] }
    }
    typeMap[type].count++
  })
  return Object.values(typeMap)
})

const closeDetailPanel = () => {
  selectedItem.value = null
  expandedSelfLoops.value = new Set()
  // Reset D3 highlights
  d3.selectAll('circle').attr('stroke', 'rgba(255,255,255,0.8)').attr('stroke-width', 2)
  d3.selectAll('path').attr('stroke', 'rgba(255,255,255,0.15)').attr('stroke-width', 1.5)
}

let currentSimulation = null
let linkLabelsRef = null
let linkLabelBgRef = null

const renderGraph = () => {
  if (!graphSvg.value || !props.graphData) return
  if (currentSimulation) currentSimulation.stop()
  
  const width = graphContainer.value.clientWidth
  const height = graphContainer.value.clientHeight
  
  const svg = d3.select(graphSvg.value)
    .attr('width', width).attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    
  svg.selectAll('*').remove()
  
  const nodesData = props.graphData.nodes || []
  const edgesData = props.graphData.edges || []
  if (nodesData.length === 0) return

  const nodeMap = {}
  nodesData.forEach(n => nodeMap[n.uuid] = n)
  const nodes = nodesData.map(n => ({ id: n.uuid, name: n.name || '?', type: n.labels?.find(l => l !== 'Entity') || 'Entity', rawData: n }))
  const nodeIds = new Set(nodes.map(n => n.id))

  const edgePairCount = {}
  const selfLoopEdges = {}
  const tempEdges = edgesData.filter(e => nodeIds.has(e.source_node_uuid) && nodeIds.has(e.target_node_uuid))

  tempEdges.forEach(e => {
    if (e.source_node_uuid === e.target_node_uuid) {
      if (!selfLoopEdges[e.source_node_uuid]) selfLoopEdges[e.source_node_uuid] = []
      selfLoopEdges[e.source_node_uuid].push({ ...e, source_name: nodeMap[e.source_node_uuid]?.name, target_name: nodeMap[e.target_node_uuid]?.name })
    } else {
      const pairKey = [e.source_node_uuid, e.target_node_uuid].sort().join('_')
      edgePairCount[pairKey] = (edgePairCount[pairKey] || 0) + 1
    }
  })

  const edgePairIndex = {}
  const processedSelfLoopNodes = new Set()
  const edges = []
  
  tempEdges.forEach(e => {
    if (e.source_node_uuid === e.target_node_uuid) {
      if (processedSelfLoopNodes.has(e.source_node_uuid)) return
      processedSelfLoopNodes.add(e.source_node_uuid)
      const loops = selfLoopEdges[e.source_node_uuid]
      edges.push({ source: e.source_node_uuid, target: e.target_node_uuid, type: 'SELF', name: `SELF (${loops.length})`, isSelfLoop: true, rawData: { isSelfLoopGroup: true, source_name: nodeMap[e.source_node_uuid]?.name, selfLoopCount: loops.length, selfLoopEdges: loops } })
      return
    }
    
    const pairKey = [e.source_node_uuid, e.target_node_uuid].sort().join('_')
    const totalCount = edgePairCount[pairKey]
    const currentIndex = edgePairIndex[pairKey] || 0
    edgePairIndex[pairKey] = currentIndex + 1
    const isReversed = e.source_node_uuid > e.target_node_uuid
    let curvature = 0
    if (totalCount > 1) {
      curvature = ((currentIndex / (totalCount - 1)) - 0.5) * (0.4 + totalCount * 0.1) * 2
      if (isReversed) curvature = -curvature
    }
    
    edges.push({ source: e.source_node_uuid, target: e.target_node_uuid, type: e.fact_type || e.name || 'LINK', name: e.name || e.fact_type || 'LINK', curvature, isSelfLoop: false, pairTotal: totalCount, rawData: { ...e, source_name: nodeMap[e.source_node_uuid]?.name, target_name: nodeMap[e.target_node_uuid]?.name } })
  })
    
  const colorMap = {}
  entityTypes.value.forEach(t => colorMap[t.name] = t.color)
  const getColor = (type) => colorMap[type] || '#444'

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(140))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide(40))
    .force('x', d3.forceX(width / 2).strength(0.05))
    .force('y', d3.forceY(height / 2).strength(0.05))
  
  currentSimulation = simulation
  const g = svg.append('g')
  svg.call(d3.zoom().scaleExtent([0.1, 8]).on('zoom', (e) => g.attr('transform', e.transform)))

  const linkGroup = g.append('g').attr('class', 'links')

  const getLinkPath = (d) => {
    const sx = d.source.x, sy = d.source.y, tx = d.target.x, ty = d.target.y
    if (d.isSelfLoop) return `M${sx+10},${sy-5} A25,25 0 1,1 ${sx+10},${sy+5}`
    if (d.curvature === 0) return `M${sx},${sy} L${tx},${ty}`
    const dx = tx - sx, dy = ty - sy, dist = Math.sqrt(dx * dx + dy * dy)
    const baseOffset = Math.max(25, dist * 0.2)
    const cx = (sx + tx) / 2 + (-dy / dist * d.curvature * baseOffset)
    const cy = (sy + ty) / 2 + (dx / dist * d.curvature * baseOffset)
    return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`
  }

  const getLinkMid = (d) => {
    const sx = d.source.x, sy = d.source.y, tx = d.target.x, ty = d.target.y
    if (d.isSelfLoop) return { x: sx + 45, y: sy }
    if (d.curvature === 0) return { x: (sx + tx) / 2, y: (sy + ty) / 2 }
    const dx = tx - sx, dy = ty - sy, dist = Math.sqrt(dx * dx + dy * dy)
    const baseOffset = Math.max(25, dist * 0.2)
    const cx = (sx + tx) / 2 + (-dy / dist * d.curvature * baseOffset)
    const cy = (sy + ty) / 2 + (dx / dist * d.curvature * baseOffset)
    return { x: 0.25 * sx + 0.5 * cx + 0.25 * tx, y: 0.25 * sy + 0.5 * cy + 0.25 * ty }
  }

  const link = linkGroup.selectAll('path').data(edges).enter().append('path')
    .attr('stroke', 'rgba(255,255,255,0.15)').attr('stroke-width', 1.5).attr('fill', 'none').style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      linkGroup.selectAll('path').attr('stroke', 'rgba(255,255,255,0.15)').attr('stroke-width', 1.5)
      d3.select(event.target).attr('stroke', '#8B5CF6').attr('stroke-width', 2.5)
      selectedItem.value = { type: 'edge', data: d.rawData }
    })

  const linkLabelBg = linkGroup.selectAll('rect').data(edges).enter().append('rect')
    .attr('fill', 'rgba(10,10,15,0.8)').attr('rx', 4).attr('ry', 4).style('display', showEdgeLabels.value ? 'block' : 'none')

  const linkLabels = linkGroup.selectAll('text').data(edges).enter().append('text')
    .text(d => d.name).attr('font-size', '8px').attr('fill', 'rgba(255,255,255,0.4)').attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
    .style('font-family', 'ui-monospace, monospace').style('font-weight', '600').style('display', showEdgeLabels.value ? 'block' : 'none')

  linkLabelsRef = linkLabels
  linkLabelBgRef = linkLabelBg

  const nodeGroup = g.append('g').attr('class', 'nodes')
  const node = nodeGroup.selectAll('circle').data(nodes).enter().append('circle')
    .attr('r', 8).attr('fill', d => getColor(d.type)).attr('stroke', 'rgba(255,255,255,0.8)').attr('stroke-width', 2)
    .style('cursor', 'pointer').style('filter', 'drop-shadow(0 0 5px currentColor)')
    .call(d3.drag().on('start', (e, d) => { d.fx = d.x; d.fy = d.y; if (!e.active) simulation.alphaTarget(0.3).restart() })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y }).on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null }))
    .on('click', (event, d) => {
      event.stopPropagation()
      node.attr('stroke', 'rgba(255,255,255,0.8)').attr('stroke-width', 2)
      d3.select(event.target).attr('stroke', '#06B6D4').attr('stroke-width', 3)
      selectedItem.value = { type: 'node', data: d.rawData, entityType: d.type, color: getColor(d.type) }
    })

  const nodeLabels = nodeGroup.selectAll('text').data(nodes).enter().append('text')
    .text(d => d.name).attr('font-size', '10px').attr('fill', 'rgba(255,255,255,0.7)')
    .attr('dx', 12).attr('dy', 4).style('pointer-events', 'none').style('font-family', 'ui-sans-serif, system-ui')

  simulation.on('tick', () => {
    link.attr('d', d => getLinkPath(d))
    linkLabels.each(function(d) { const mid = getLinkMid(d); d3.select(this).attr('x', mid.x).attr('y', mid.y) })
    linkLabelBg.each(function(d, i) { 
      const mid = getLinkMid(d); const bbox = linkLabels.nodes()[i].getBBox()
      d3.select(this).attr('x', mid.x - bbox.width/2 - 4).attr('y', mid.y - bbox.height/2 - 2).attr('width', bbox.width + 8).attr('height', bbox.height + 4)
    })
    node.attr('cx', d => d.x).attr('cy', d => d.y)
    nodeLabels.attr('x', d => d.x).attr('y', d => d.y)
  })

  svg.on('click', () => {
    closeDetailPanel()
    linkGroup.selectAll('path').attr('stroke', 'rgba(255,255,255,0.15)').attr('stroke-width', 1.5)
  })
}

watch(() => props.graphData, () => nextTick(renderGraph), { deep: true })
watch(showEdgeLabels, (nv) => {
  if (linkLabelsRef) linkLabelsRef.style('display', nv ? 'block' : 'none')
  if (linkLabelBgRef) linkLabelBgRef.style('display', nv ? 'block' : 'none')
})

const handleResize = () => renderGraph()
onMounted(() => { window.addEventListener('resize', handleResize); nextTick(renderGraph) })
onUnmounted(() => window.removeEventListener('resize', handleResize))
</script>

<style scoped>
.shadow-glow { filter: drop-shadow(0 0 4px var(--tw-shadow-color)); }
.shadow-glow-cyan { filter: drop-shadow(0 0 10px rgba(6, 182, 212, 0.4)); }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.slide-left-enter-active, .slide-left-leave-active { transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1); }
.slide-left-enter-from, .slide-left-leave-to { transform: translateX(40px); opacity: 0; }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.4s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translate(-50%, -20px); opacity: 0; }
</style>
