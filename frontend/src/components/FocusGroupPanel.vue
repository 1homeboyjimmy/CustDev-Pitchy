<template>
  <div class="space-y-6">
    <!-- Персоны: карточки с раскрытием профиля -->
    <section>
      <div class="flex items-center gap-2 mb-3 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">
        <UsersIcon class="w-3.5 h-3.5" /> Персоны · кликни, чтобы открыть профиль и чат
      </div>
      <div v-if="!profiles || profiles.length === 0" class="text-white/30 text-sm py-6 text-center border border-white/5 rounded-2xl">
        Персоны ещё не сгенерированы…
      </div>
      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <button
          v-for="(p, idx) in profiles"
          :key="p.username || idx"
          @click="select(p)"
          class="text-left rounded-2xl border p-3.5 transition-all"
          :class="isActive(p) ? 'bg-white/[0.06] border-white/25' : 'bg-white/[0.03] border-white/10 hover:border-white/20'"
        >
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl shrink-0 flex items-center justify-center text-xs font-black bg-white/10 text-white border border-white/15">
              {{ (p.username || '?').charAt(0).toUpperCase() }}
            </div>
            <div class="min-w-0">
              <div class="text-sm font-bold text-white truncate">{{ p.username || p.name }}</div>
              <div class="text-[10px] text-white/40 truncate uppercase tracking-wide">{{ p.profession || '—' }}</div>
            </div>
          </div>
          <div v-if="isActive(p)" class="mt-3 pt-3 border-t border-white/10 space-y-2.5">
            <div class="flex flex-wrap gap-1.5">
              <span v-for="chip in chips(p)" :key="chip" class="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/55">{{ chip }}</span>
            </div>
            <p v-if="p.persona || p.bio" class="text-[12px] leading-relaxed text-white/65">{{ p.persona || p.bio }}</p>
          </div>
        </button>
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
          class="bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.15)] rounded-full px-5 py-2 text-sm font-bold disabled:opacity-40 inline-flex items-center gap-2"
        >
          <LoaderIcon v-if="running" class="w-4 h-4 animate-spin" />
          <PlayIcon v-else class="w-4 h-4" />
          Провести CustDev-интервью
        </button>
      </div>

      <div v-else class="space-y-2.5">
        <div
          v-for="(q, qi) in interviewQuestions"
          :key="qi"
          class="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden"
        >
          <button @click="toggle(qi)" class="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-white/[0.02]">
            <span class="text-sm text-white font-medium">{{ qi + 1 }}. {{ q }}</span>
            <span class="flex items-center gap-2 shrink-0">
              <span class="text-[10px] font-mono text-white/30">{{ answersFor(q).length }}/{{ profilesCount }}</span>
              <ChevronDownIcon class="w-4 h-4 text-white/30 transition-transform" :class="{ 'rotate-180': open.has(qi) }" />
            </span>
          </button>
          <div v-if="open.has(qi)" class="px-4 pb-4 pt-1 border-t border-white/5 space-y-2">
            <div v-if="answersFor(q).length === 0" class="text-white/30 text-xs py-2">Ответов пока нет…</div>
            <div
              v-for="(a, ai) in answersFor(q)"
              :key="ai"
              class="rounded-xl bg-white/[0.03] border border-white/8 p-3"
            >
              <div class="flex items-center gap-2 mb-1">
                <span class="text-[12px] font-bold text-white">{{ a.agent_name }}</span>
                <span class="text-[10px] text-white/30 uppercase tracking-wide">{{ a.agent_role }}</span>
              </div>
              <p class="text-[12.5px] leading-relaxed text-white/75">{{ a.response }}</p>
              <ul v-if="a.key_quotes && a.key_quotes.length" class="mt-2 space-y-1">
                <li v-for="(quote, ki) in a.key_quotes.slice(0, 2)" :key="ki" class="text-[11px] italic text-white/45 border-l-2 border-white/20 pl-2">«{{ quote }}»</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 1-на-1 чат с выбранной персоной -->
    <section class="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
      <div class="flex items-center gap-2 mb-3 text-white/40 text-[10px] font-bold uppercase tracking-[0.2em]">
        <MessageIcon class="w-3.5 h-3.5" /> Поговорить лично
        <span v-if="selected" class="text-white/55 normal-case tracking-normal">— {{ selected.username || selected.name }}</span>
      </div>

      <div v-if="!selected" class="text-white/30 text-sm py-4 text-center">Выберите персону выше, чтобы задать ей вопрос.</div>

      <template v-else>
        <div class="space-y-2 mb-3 max-h-72 overflow-y-auto custom-scrollbar">
          <div v-if="chatHistory.length === 0" class="text-white/25 text-xs py-3 text-center">Спросите что угодно у этого агента.</div>
          <div
            v-for="(m, mi) in chatHistory"
            :key="mi"
            class="text-[12.5px] leading-relaxed rounded-2xl px-3 py-2 max-w-[88%]"
            :class="m.role === 'user'
              ? 'ml-auto bg-white/[0.07] text-white rounded-br-sm'
              : 'bg-white/[0.03] border border-white/8 text-white/80 rounded-bl-sm'"
          >{{ m.content }}</div>
        </div>
        <div class="flex gap-2">
          <input
            v-model="draft"
            @keydown.enter="emitSend"
            type="text"
            placeholder="Спросите что угодно у этого агента…"
            class="flex-1 bg-white/[0.04] border border-white/12 rounded-full px-4 py-2 text-sm text-white outline-none focus:border-white/40"
          />
          <button
            @click="emitSend"
            :disabled="sending || !draft.trim()"
            class="bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.15)] rounded-full px-4 py-2 text-sm font-bold disabled:opacity-40 flex items-center gap-1"
          >
            <SendIcon class="w-4 h-4" />
          </button>
        </div>
      </template>
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
} from 'lucide-vue-next'

const props = defineProps({
  profiles: { type: Array, default: () => [] },
  interviewQuestions: { type: Array, default: () => [] },
  interviews: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  chatHistory: { type: Array, default: () => [] },
  sending: { type: Boolean, default: false },
  running: { type: Boolean, default: false },
})

const emit = defineEmits(['select-agent', 'send', 'run-interview'])

const open = ref(new Set([0]))
const draft = ref('')

const profilesCount = computed(() => props.profiles.length || 0)

const isActive = (p) => props.selected && (props.selected.username === p.username || props.selected === p)
const select = (p) => emit('select-agent', p)

const toggle = (qi) => {
  const s = new Set(open.value)
  s.has(qi) ? s.delete(qi) : s.add(qi)
  open.value = s
}

const answersFor = (q) => props.interviews.filter((i) => i.question === q)

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
  if (!text || props.sending) return
  emit('send', text)
  draft.value = ''
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 10px; }
</style>
