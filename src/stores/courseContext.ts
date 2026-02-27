import { writable, get } from 'svelte/store';
import axios from 'axios';

export type CourseContext = {
  id: number | null;
  courseCode: string;
  courseTitle: string;
  learningOutcomes: string;
  canvasCourseId: string;
};

export type CourseListItem = {
  id: number;
  courseCode: string;
  courseTitle: string;
  learningOutcomes: string;
  canvasCourseId: string | null;
};

const STORAGE_KEY = 'rhizome_course_context';

function empty(): CourseContext {
  return { id: null, courseCode: '', courseTitle: '', learningOutcomes: '', canvasCourseId: '' };
}

function loadFromStorage(): CourseContext {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...empty(), ...JSON.parse(raw) };
  } catch (err) {
    console.error('[courseContext] Failed to read from localStorage — starting fresh:', err);
  }
  return empty();
}

export const courseContext = writable<CourseContext>(loadFromStorage());
export const courseList = writable<CourseListItem[]>([]);

courseContext.subscribe(value => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch (err) {
    console.error('[courseContext] Failed to persist to localStorage:', err);
  }
});

export async function loadCourses(): Promise<void> {
  try {
    const res = await axios.get('/api/courses', { withCredentials: true });
    const courses: CourseListItem[] = res.data.courses;
    courseList.set(courses);
    const current = get(courseContext);
    if (!current.id && courses.length > 0) {
      const first = courses[0];
      courseContext.set({
        id: first.id,
        courseCode: first.courseCode,
        courseTitle: first.courseTitle,
        learningOutcomes: first.learningOutcomes,
        canvasCourseId: first.canvasCourseId ?? '',
      });
    }
  } catch (err) {
    console.error('[courseContext] loadCourses failed:', err);
    throw err;
  }
}

export async function saveCourse(): Promise<void> {
  const ctx = get(courseContext);
  try {
    const res = await axios.post(
      '/api/courses',
      {
        id: ctx.id,
        courseCode: ctx.courseCode,
        courseTitle: ctx.courseTitle,
        learningOutcomes: ctx.learningOutcomes,
        canvasCourseId: ctx.canvasCourseId || null,
      },
      { withCredentials: true }
    );
    const saved = res.data;
    courseContext.update(c => ({ ...c, id: saved.id }));
    await loadCourses();
  } catch (err) {
    console.error('[courseContext] saveCourse failed:', err);
    throw err;
  }
}

export function selectCourse(item: CourseListItem): void {
  courseContext.set({
    id: item.id,
    courseCode: item.courseCode,
    courseTitle: item.courseTitle,
    learningOutcomes: item.learningOutcomes,
    canvasCourseId: item.canvasCourseId ?? '',
  });
}

export function newCourse(): void {
  courseContext.set(empty());
}

export function clearCourseContext(): void {
  localStorage.removeItem(STORAGE_KEY);
  courseContext.set(empty());
}
