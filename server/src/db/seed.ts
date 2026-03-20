/**
 * Seed — demo user + MARI 515 (mirrors backend/seed.py).
 * Run: DATABASE_URL=postgres://localhost/rhizome-builder npx tsx src/db/seed.ts
 */

import { getSql } from "./index.js"
import * as q from "./queries.js"

const sql = getSql()

const user = await q.createDemoUser(sql)
console.log("user:", user.id, user.name)

const course = await q.createCourse(
  sql,
  user.id as number,
  "MARI 515",
  "Coral Ecology and Conservation",
  [
    "Identify the physiological mechanisms underlying coral bleaching and evaluate the relative contribution of thermal stress, ocean acidification, and local stressors.",
    "Analyze a reef system using field or remotely-sensed data and characterize its current health state, trajectory, and dominant stressors.",
    "Evaluate restoration intervention strategies — including coral gardening, assisted gene flow, and substrate stabilization — against the ecological and logistical constraints of a specific site.",
    "Articulate a monitoring protocol that could detect early warning signals of degradation before bleaching thresholds are reached.",
    "Situate a conservation decision within the social and political context of the reef — including Indigenous stewardship, tourism economies, and fisheries — and defend the tradeoffs made.",
  ].join("\n"),
)
console.log("course:", course.id, course.courseCode)

const outcomes = [
  "Identify the physiological mechanisms underlying coral bleaching and evaluate the relative contribution of thermal stress, ocean acidification, and local stressors.",
  "Analyze a reef system using field or remotely-sensed data and characterize its current health state, trajectory, and dominant stressors.",
  "Evaluate restoration intervention strategies — including coral gardening, assisted gene flow, and substrate stabilization — against the ecological and logistical constraints of a specific site.",
  "Articulate a monitoring protocol that could detect early warning signals of degradation before bleaching thresholds are reached.",
  "Situate a conservation decision within the social and political context of the reef — including Indigenous stewardship, tourism economies, and fisheries — and defend the tradeoffs made.",
]
for (const [i, text] of outcomes.entries()) {
  await q.createLearningOutcome(sql, course.id as number, text, i)
  console.log("  outcome", i + 1)
}

const weeks = [
  ["Week 1", "Coral Biology Foundations"],
  ["Week 2", "Thermal Stress and Bleaching"],
  ["Week 3", "Ocean Acidification"],
  ["Week 4", "Field Survey Methods"],
  ["Week 5", "Remote Sensing for Reef Monitoring"],
  ["Week 6", "Reef Health Assessment"],
  ["Week 7", "Restoration Strategies I"],
  ["Week 8", "Restoration Strategies II"],
  ["Week 9", "Monitoring Protocol Design"],
  ["Week 10", "Socioecological Context"],
  ["Week 11", "Stakeholder Engagement"],
  ["Week 12", "Policy and Governance"],
  ["Week 13", "Case Studies"],
  ["Week 14", "Synthesis and Integration"],
  ["Week 15", "Final Project Workshop"],
]
for (const [i, [label, title]] of weeks.entries()) {
  await q.createModule(sql, course.id as number, title, "", i, [], undefined)
  console.log(" ", label, title)
}

console.log("seed complete")
await sql.end()
