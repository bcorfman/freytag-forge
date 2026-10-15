export function authoredDeliveryReasons(bundle) {
  if (bundle?.outcome !== "committed") return [];
  const reasons = [];
  if (bundle.transition_cause === "forced") reasons.push("forced_handoff");
  if (bundle.transition_cause === "timer") reasons.push("timer_handoff");
  if (bundle.story_complete === true) reasons.push("ending");
  if (bundle.cue_stage?.delivered === true) reasons.push("cue_delivered");
  if (Array.isArray(bundle.selected_reveal?.delivery_fact_ids) && bundle.selected_reveal.delivery_fact_ids.length) {
    reasons.push("delivery_facts");
  }
  return reasons;
}
