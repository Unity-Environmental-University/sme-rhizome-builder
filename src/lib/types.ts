/**
 * Shared types for the rhizome-builder frontend.
 * Extracted from CourseMap.svelte and ModuleView.svelte where they were duplicated.
 */

export type OutcomeRow = {
  id: number;
  text: string;
  position: number;
};

export type AssignmentSnapshot = {
  id: number;
  label: string | null;
  description: string;
};

export type AssignmentStub = {
  id: string;
  title: string;
  moduleLabel: string;
  position: number | null;
  snapshot: AssignmentSnapshot | null;
};

export type CourseShape = {
  id: number;
  code: string;
  title: string;
  description: string;
  periodType: string;
  outcomes: string[];
  outcomeRows: OutcomeRow[];
};

export type ModuleShape = {
  id: number;
  week: number;
  title: string;
  description: string;
  outcomeIds: number[];
  assignments: AssignmentStub[];
};

export type View =
  | { kind: 'course' }
  | { kind: 'module'; week: number }
  | { kind: 'editor'; week: number; assignmentId: string; isNew?: boolean }
  | { kind: 'designer' };
