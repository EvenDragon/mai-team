const BASE = import.meta.env.VITE_API_URL || "/api";
export const token = () => sessionStorage.getItem("mai.session");
export function saveToken(value) {
  if (value) sessionStorage.setItem("mai.session", value);
  else sessionStorage.removeItem("mai.session");
}
export async function api(path, options = {}) {
  const { body, ...rest } = options;
  let response;
  try {
    response = await fetch(BASE + path, {
      ...rest,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(
      "Не удалось связаться с сервером. Проверьте подключение и повторите попытку.",
    );
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && token()) {
      saveToken(null);
      window.dispatchEvent(new Event("session-expired"));
    }
    const fields = data.errors
      ?.map((e) => `${e.field.replace("body.", "")}: ${e.message}`)
      .join("; ");
    throw new Error(
      (typeof data.detail === "string"
        ? data.detail
        : "Не удалось выполнить действие") + (fields ? `. ${fields}` : ""),
    );
  }
  return data;
}
export const post = (path, body) => api(path, { method: "POST", body });
export const put = (path, body) => api(path, { method: "PUT", body });
export const categories = [
  "IT",
  "Инженерия",
  "Наука",
  "Социальные проекты",
  "Дизайн",
];
export const formats = ["Онлайн", "Очно", "Гибрид"];
export const labels = {
  pending: "На рассмотрении",
  published: "Опубликован",
  rejected: "Отклонён",
  hidden: "Скрыт",
  accepted: "В команде",
  withdrawn: "Отозван",
  left: "Вы вышли",
  removed: "Участие завершено",
  resolved: "Рассмотрена",
  spam: "Спам или реклама",
  abuse: "Оскорбления",
  fraud: "Обман",
  other: "Другое",
  dismiss: "Нарушения нет",
  warn: "Замечание",
  hide: "Проект скрыт",
  block: "Блокировка",
  unblock: "Разблокировка",
};
export const splitSkills = (value) => [
  ...new Set(
    value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  ),
];
