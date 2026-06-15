<template>
  <div class="space-y-6">
    <!-- Персоны -->
    <section>
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">
          <UsersIcon class="w-3.5 h-3.5" /> Персоны общества
        </div>
        <div v-if="interviewDone" class="flex items-center gap-3 text-[11px]">
          <span class="text-orange-400 flex items-center gap-1"><FlameIcon class="w-3 h-3" /> {{ warmthCount('hot') }}</span>
          <span class="text-amber-300 flex items-center gap-1"><ThermoIcon class="w-3 h-3" /> {{ warmthCount('warm') }}</span>
          <span class="text-sky-400 flex items-center gap-1"><SnowIcon class="w-3 h-3" /> {{ warmthCount('cold') }}</span>
        </div>
      </div>

      <div v-if="!profiles || profiles.length === 0" class="text-white/30 text-sm py-6 text-center border border-white/5 rounded-2xl">
        Персоны ещё не сгенерированы…
      </div>

      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <div
          v-for="(p, idx) in profiles"
          :key="p.username || idx"
          class="rounded-2xl border transition-all overflow-hidden"
          :class="isActive(p) ? 'bg-white/[0.06] border-white/25 sm:col-span-2 lg:col-span-3' : 'bg-white/[0.03] border-white/10 hover:border-white/20'"
        >
          <button @click="select(p)" class="w-full text-left p-3.5">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full shrink-0 flex items-center justify-center text-sm font-black bg-white/10 text-white border border-white/15">
                {{ initials(p) }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="text-sm font-bold text-white truncate">{{ p.username || p.name }}</div>
                <div class="text-[10px] text-white/40 truncate uppercase tracking-wide">{{ p.profession || '—' }}</div>
              </div>
              <span v-if="interviewDone && warmthOf(p)" class="text-[11px] flex items-center gap-1 shrink-0" :class="tempColor(warmthOf(p))">
                <component :is="tempIcon(warmthOf(p))" class="w-3.5 h-3.5" /> {{ tempLabel(warmthOf(p)) }}
              </span>
            </div>
          </button>

          <!-- Раскрытая карточка: характеристики + чат (чат после интервью) -->
          <div v-if="isActive(p)" class="px-3.5 pb-3.5 space-y-3 border-t border-white/10 pt-3">
            <div class="flex flex-wrap gap-1.5">
              <span v-for="chip in chips(p)" :key="chip" class="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/55">{{ chip }}</span>
            </div>
            <p v-if="p.persona || p.bio" class="text-[12px] leading-relaxed text-white/65">{{ p.persona || p.bio }}</p>

            <!-- Личный чат -->
            <div class="pt-1">
              <div v-if="!interviewDone" class="text-[12px] text-white/35 flex items-center gap-2 py-2">
                <LockIcon class="w-3.5 h-3.5" /> Поговорить лично можно после прохождения интервью
              </div>
              <template v-else>
                <div class="flex items-center gap-2 mb-2 text-white/40 text-[10px] font-bold uppercase tracking-[0.15em]">
                  <MessageIcon class="w-3.5 h-3.5" /> Личный разговор
                </div>
                <div class="space-y-2 mb-2 max-h-64 overflow-y-auto custom-scrollbar">
                  <div v-if="chatHistory.length === 0" class="text-white/25 text-xs py-2">Агент помнит свои ответы из интервью — спросите что угодно.</div>
                  <div
                    v-for="(m, mi) in chatHistory"
                    :key="mi"
                    class="text-[12.5px] leading-relaxed rounded-2xl px-3 py-2 max-w-[88%]"
                    :class="m.role === 'user' ? 'ml-auto bg-white/[0.08] text-white rounded-br-sm' : 'bg-white/[0.03] border border-white/8 text-white/80 rounded-bl-sm'"
                  >{{ m.content }}</div>
                </div>
                <div class="flex gap-2">
                  <input
                    v-model="draft"
                    @keydown.enter="emitSend"
                    type="text"
                    :placeholder="`Спросить лично у ${(p.username || p.name)}…`"
                    class="flex-1 bg-white/[0.04] border border-white/12 rounded-full px-4 py-2 text-sm text-white outline-none focus:border-white/40"
                  />
                  <button @click="emitSend" :disabled="sending || !draft.trim()" class="bg-white text-black rounded-full px-4 py-2 text-sm font-bold disabled:opacity-40 flex items-center gap-1">
                    <SendIcon class="w-4 h-4" />
                  </button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Интервью: аккордеон фикс-вопросов -->
    <section>
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">
          <ListChecksIcon class="w-3.5 h-3.5" /> Стандартное CustDev-интервью
        </div>
        <span v-if="running" class="text-[10px] text-white flex items-center gap-1.5"><LoaderIcon class="w-3 h-3 animate-spin" /> идёт интервью…</span>
        <span v-else-if="interviewQuestions.length" class="text-[10px] text-white/30">{{ interviewQuestions.length }} вопросов</span>
      </div>

      <div v-if="interviewQuestions.length === 0" class="py-6 text-center border border-white/5 rounded-2xl">
        <p class="text-white/30 text-sm mb-3">Общество ответит на стандартный список CustDev-вопросов.</p>
        <button
          @click="$emit('run-interview')"
          :disabled="running || !profiles || profiles.length === 0"
          class="bg-white text-black rounded-full px-5 py-2 text-sm font-bold disabled:opacity-40 inline-flex items-center gap-2 shadow-[0_0_24px_rgba(255,255,255,0.1)]"
        >
          <LoaderIcon v-if="running" class="w-4 h-4 animate-spin" />
          <PlayIcon v-else class="w-4 h-4" />
          Провести CustDev-интервью
        </button>
      </div>

      <div v-else class="space-y-2.5">
        <div v-for="(q, qi) in interviewQuestions" :key="qi" class="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
          <button @click="toggle(qi)" class="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-white/[0.02]">
            <span class="text-sm text-white font-medium">{{ qi + 1 }}. {{ q }}</span>
            <span class="flex items-center gap-2 shrink-0">
              <span class="text-[10px] font-mono text-white/30">{{ answersFor(q).length }}/{{ profilesCount }}</span>
              <ChevronDownIcon class="w-4 h-4 text-white/30 transition-transform" :class="{ 'rotate-180': open.has(qi) }" />
            </span>
          </button>
          <div v-if="open.has(qi)" class="px-4 pb-4 pt-1 border-t border-white/5 space-y-3">
            <div v-if="answersFor(q).length === 0" class="text-white/30 text-xs py-2">Ответов пока нет…</div>
            <div v-for="(a, ai) in answersFor(q)" :key="ai" class="flex gap-3">
              <div class="w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-[11px] font-bold bg-white/10 text-white border border-white/12">{{ initialsName(a.agent_name) }}</div>
              <div class="min-w-0">
                <div class="text-[11px] text-white/40 mb-0.5">{{ a.agent_name }}<span v-if="a.agent_role"> · {{ a.agent_role }}</span></div>
                <p class="text-[12.5px] leading-relaxed text-white/75">{{ a.response }}</p>
                <ul v-if="a.key_quotes && a.key_quotes.length" class="mt-1.5 space-y-1">
                  <li v-for="(quote, ki) in a.key_quotes.slice(0, 2)" :key="ki" class="text-[11px] italic text-white/45 border-l-2 border-white/20 pl-2">«{{ quote }}»</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  Users as UsersIcon,
  ListChecks as ListChecksIcon,
  ChevronDown as ChevronDownIcon,
  MessageCircle as MessageIcon,
  Send as SendIcon,
  Loader as LoaderIcon,
  Play as PlayIcon,
  Lock as LockIcon,
  Flame as FlameIcon,
  Thermometer as ThermoIcon,
  Snowflake as SnowIcon,
} from 'lucide-vue-next'

const props = defineProps({
  profiles: { type: Array, default: () => [] },
  interviewQuestions: { type: Array, default: () => [] },
  interviews: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  chatHistory: { type: Array, default: () => [] },
  sending: { type: Boolean, default: false },
  running: { type: Boolean, default: false },
  interviewDone: { type: Boolean, default: false },
  warmth: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['select-agent', 'send', 'run-interview'])

const open = ref(new Set([0]))
const draft = ref('')

const profilesCount = computed(() => props.profiles.length || 0)

const nameOf = (p) => p.username || p.name || ''
const isActive = (p) => props.selected && (props.selected.username === p.username || props.selected === p)
const select = (p) => emit('select-agent', p)

const toggle = (qi) => {
  const s = new Set(open.value)
  s.has(qi) ? s.delete(qi) : s.add(qi)
  open.value = s
}

const answersFor = (q) => props.interviews.filter((i) => i.question === q)

const initialsName = (name) => (name || '?').trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
const initials = (p) => initialsName(nameOf(p))

const warmthOf = (p) => props.warmth[nameOf(p)]
const warmthCount = (level) => Object.values(props.warmth).filter(v => v === level).length
const tempIcon = (t) => (t === 'hot' ? FlameIcon : t === 'warm' ? ThermoIcon : SnowIcon)
const tempColor = (t) => (t === 'hot' ? 'text-orange-400' : t === 'warm' ? 'text-amber-300' : 'text-sky-400')
const tempLabel = (t) => (t === 'hot' ? 'Горит' : t === 'warm' ? 'Тепло' : 'Холодно')

const chips = (p) => {
  const out = []
  if (p.age) out.push(`Возраст: ${p.age}`)
  if (p.mbti) out.push(p.mbti)
  if (p.country) out.push(p.country)
  if (p.gender) out.push(p.gender)
  if (Array.isArray(p.interested_topics) && p.interested_topics.length) out.push(p.interested_topics.slice(0, 2).join(', '))
  return out
}

const emitSend = () => {
  const text = draft.value.trim()
  if (!text || props.sending || !props.interviewDone) return
  emit('send', text)
  draft.value = ''
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 10px; }
</style>
