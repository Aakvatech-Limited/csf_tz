const listeners = new Map();

export const evntBus = {
  $on(event, handler) {
    if (!listeners.has(event)) {
      listeners.set(event, new Set());
    }
    listeners.get(event).add(handler);
  },

  $off(event, handler) {
    const handlers = listeners.get(event);
    if (!handlers) return;

    handlers.delete(handler);
    if (!handlers.size) {
      listeners.delete(event);
    }
  },

  $emit(event, payload) {
    const handlers = listeners.get(event);
    if (!handlers) return;

    handlers.forEach((handler) => handler(payload));
  },
};
