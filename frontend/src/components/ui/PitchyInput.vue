<template>
  <div class="w-full flex flex-col gap-1.5 font-sans">
    <label v-if="label" class="text-[11px] font-bold text-white/40 uppercase tracking-widest pl-1 font-display">
      {{ label }}
    </label>
    <div class="relative flex items-center group">
      <div v-if="$slots.icon" class="absolute left-4 text-white/30 group-focus-within:text-white transition-colors">
        <slot name="icon"></slot>
      </div>
      <input
        v-bind="$attrs"
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)"
        class="pitchy-input w-full transition-all duration-200"
        :class="{ 'pl-11': $slots.icon }"
        :placeholder="placeholder"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: [String, Number],
  label: String,
  placeholder: String
})

defineEmits(['update:modelValue'])
</script>

<script>
export default {
  inheritAttrs: false
}
</script>
