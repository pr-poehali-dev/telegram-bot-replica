import { useState } from "react";
import Icon from "@/components/ui/icon";

type Section = "analysis" | "search" | "stats" | "segments" | "export" | "help";

const NAV_ITEMS: { id: Section; label: string; icon: string; color: string }[] = [
  { id: "analysis", label: "Анализ", icon: "ScanSearch", color: "cyan" },
  { id: "search", label: "Поиск", icon: "Search", color: "violet" },
  { id: "stats", label: "Статистика", icon: "BarChart3", color: "green" },
  { id: "segments", label: "Сегменты", icon: "Layers", color: "orange" },
  { id: "export", label: "Экспорт", icon: "Download", color: "cyan" },
  { id: "help", label: "Помощь", icon: "LifeBuoy", color: "violet" },
];

const COLOR_MAP: Record<string, { text: string; border: string; bg: string }> = {
  cyan:   { text: "text-cyan-400",    border: "border-cyan-500/30",    bg: "bg-cyan-500/10" },
  violet: { text: "text-violet-400",  border: "border-violet-500/30",  bg: "bg-violet-500/10" },
  green:  { text: "text-emerald-400", border: "border-emerald-500/30", bg: "bg-emerald-500/10" },
  orange: { text: "text-orange-400",  border: "border-orange-500/30",  bg: "bg-orange-500/10" },
};

function ActivityChart() {
  const hours = ["00","03","06","09","12","15","18","21"];
  const bars = [18, 32, 12, 45, 78, 92, 67, 55];
  return (
    <div className="flex items-end gap-1.5 h-20">
      {bars.map((val, i) => (
        <div key={i} className="flex flex-col items-center gap-1 flex-1">
          <div
            className="w-full rounded-sm"
            style={{
              height: `${val}%`,
              background: "linear-gradient(to top, hsl(195,100%,50%), hsl(270,80%,65%))",
              opacity: 0.6 + val / 300,
            }}
          />
          <span className="text-[9px] text-muted-foreground">{hours[i]}</span>
        </div>
      ))}
    </div>
  );
}

function StatBar({ label, value, color }: { label: string; value: number; color: string }) {
  const c = COLOR_MAP[color];
  const barColor = color === "cyan" ? "hsl(195,100%,50%)" : color === "violet" ? "hsl(270,80%,65%)" : color === "green" ? "hsl(142,80%,50%)" : "hsl(32,100%,55%)";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={c.text + " font-medium"}>{value}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value}%`, background: barColor }} />
      </div>
    </div>
  );
}

function AnalysisSection() {
  const [username, setUsername] = useState("");
  const [searched, setSearched] = useState(false);

  return (
    <div className="space-y-4 animate-fade-up-1">
      <div className="glass rounded-xl p-5 border border-cyan-500/20">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-2 h-2 rounded-full bg-cyan-400 pulse-dot" />
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Анализ профиля</span>
        </div>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-400 text-sm">@</span>
            <input
              value={username}
              onChange={e => setUsername(e.target.value)}
              onKeyDown={e => e.key === "Enter" && username && setSearched(true)}
              placeholder="username"
              className="w-full bg-secondary border border-border rounded-lg pl-7 pr-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-cyan-500/50 transition-colors"
            />
          </div>
          <button
            onClick={() => username && setSearched(true)}
            className="px-4 py-2.5 rounded-lg text-sm font-medium text-background transition-all hover:opacity-90 active:scale-95"
            style={{ background: "hsl(195,100%,50%)" }}
          >
            Искать
          </button>
        </div>
      </div>

      {searched && (
        <div className="glass rounded-xl p-5 border border-cyan-500/20 animate-fade-in space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-display font-bold text-background"
              style={{ background: "linear-gradient(135deg, hsl(195,100%,50%), hsl(270,80%,65%))" }}>
              {username[0]?.toUpperCase() || "U"}
            </div>
            <div>
              <div className="font-display font-semibold text-base text-foreground">@{username}</div>
              <div className="text-xs text-muted-foreground">ID: 4872319 · Активен сегодня</div>
            </div>
            <div className="ml-auto">
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">Реальный</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Сообщений", value: "3 241", icon: "MessageSquare", color: "cyan" },
              { label: "Чатов", value: "47", icon: "Users", color: "violet" },
              { label: "Медиа", value: "218", icon: "Image", color: "green" },
            ].map((s, i) => {
              const c = COLOR_MAP[s.color];
              return (
                <div key={i} className={`rounded-lg p-3 border ${c.border} ${c.bg}`}>
                  <Icon name={s.icon} size={14} className={c.text + " mb-1"} />
                  <div className={`text-lg font-display font-bold ${c.text}`}>{s.value}</div>
                  <div className="text-[10px] text-muted-foreground">{s.label}</div>
                </div>
              );
            })}
          </div>

          <div>
            <div className="text-xs text-muted-foreground mb-2">История никнеймов</div>
            <div className="flex flex-wrap gap-1.5">
              {["@old_nick", "@prev_user", `@${username}`].map((n, i) => (
                <span key={i} className="text-xs px-2 py-0.5 rounded-full font-medium bg-secondary text-muted-foreground border border-border">{n}</span>
              ))}
            </div>
          </div>

          <div>
            <div className="text-xs text-muted-foreground mb-2">Публичные группы</div>
            <div className="space-y-1.5">
              {["Crypto Signals RU", "Python Developers", "OSINT Community"].map((g, i) => (
                <div key={i} className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-secondary/50 text-sm">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span className="text-foreground/80">{g}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{[1240, 8920, 4310][i]} участн.</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="glass rounded-xl p-5 border border-border">
        <div className="text-xs text-muted-foreground mb-3 uppercase tracking-widest">Активность по времени суток</div>
        <ActivityChart />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="glass rounded-xl p-4 border border-violet-500/20">
          <Icon name="Phone" size={14} className="text-violet-400 mb-2" />
          <div className="text-xs text-muted-foreground mb-1">Телефон</div>
          <div className="text-sm font-medium text-foreground/60">+7 *** ***-**-**</div>
        </div>
        <div className="glass rounded-xl p-4 border border-orange-500/20">
          <Icon name="Clock" size={14} className="text-orange-400 mb-2" />
          <div className="text-xs text-muted-foreground mb-1">Регистрация</div>
          <div className="text-sm font-medium text-foreground/80">~2019 год</div>
        </div>
      </div>
    </div>
  );
}

function SearchSection() {
  const [query, setQuery] = useState("");
  const results = [
    { name: "OSINT Russia", type: "канал", members: "12 400", active: true },
    { name: "CyberSec Chat", type: "группа", members: "5 820", active: true },
    { name: "DataLeaks RU", type: "группа", members: "3 100", active: false },
    { name: "Digital Forensics", type: "канал", members: "9 700", active: true },
  ];

  return (
    <div className="space-y-4 animate-fade-up-1">
      <div className="glass rounded-xl p-5 border border-violet-500/20">
        <div className="flex items-center gap-2 mb-4">
          <Icon name="Search" size={14} className="text-violet-400" />
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Поиск чатов и каналов</span>
        </div>
        <div className="space-y-3">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Ключевое слово..."
            className="w-full bg-secondary border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-violet-500/50 transition-colors"
          />
          <div className="flex gap-2 flex-wrap">
            {["OSINT", "маркетинг", "безопасность", "крипто"].map(tag => (
              <button
                key={tag}
                onClick={() => setQuery(tag)}
                className="text-xs px-2 py-0.5 rounded-full font-medium bg-violet-500/10 text-violet-400 border border-violet-500/25 hover:bg-violet-500/20 transition-colors cursor-pointer"
              >
                {tag}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <select className="bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-violet-500/50">
              <option>Любой тип</option>
              <option>Каналы</option>
              <option>Группы</option>
            </select>
            <select className="bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-violet-500/50">
              <option>Любой язык</option>
              <option>Русский</option>
              <option>Английский</option>
            </select>
          </div>
          <button className="w-full py-2.5 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90"
            style={{ background: "hsl(270,80%,65%)" }}>
            Найти
          </button>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs text-muted-foreground px-1">Результаты поиска</div>
        {results.map((r, i) => (
          <div key={i} className="glass glass-hover rounded-xl p-4 border border-border flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-base font-display font-bold flex-shrink-0 text-white"
              style={{ background: `linear-gradient(135deg, hsl(270,80%,${35 + i * 8}%), hsl(195,100%,${40 + i * 5}%))` }}>
              {r.name[0]}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-foreground truncate">{r.name}</div>
              <div className="text-xs text-muted-foreground">{r.members} участн. · {r.type}</div>
            </div>
            <div className="flex items-center gap-2">
              {r.active && <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
              <Icon name="ChevronRight" size={14} className="text-muted-foreground" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatsSection() {
  return (
    <div className="space-y-4 animate-fade-up-1">
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Проанализировано", value: "184K", sub: "пользователей", icon: "Users", color: "cyan" },
          { label: "Чатов в базе", value: "32K", sub: "публичных", icon: "MessageSquare", color: "violet" },
          { label: "Запросов сегодня", value: "4 721", sub: "за 24 ч", icon: "Zap", color: "green" },
          { label: "Точность", value: "98.4%", sub: "верификация", icon: "ShieldCheck", color: "orange" },
        ].map((s, i) => {
          const c = COLOR_MAP[s.color];
          return (
            <div key={i} className={`glass rounded-xl p-4 border ${c.border}`}>
              <Icon name={s.icon} size={16} className={c.text + " mb-2"} />
              <div className={`text-2xl font-display font-bold ${c.text}`}>{s.value}</div>
              <div className="text-xs text-foreground/70 font-medium">{s.label}</div>
              <div className="text-[10px] text-muted-foreground">{s.sub}</div>
            </div>
          );
        })}
      </div>

      <div className="glass rounded-xl p-5 border border-border">
        <div className="text-xs text-muted-foreground uppercase tracking-widest mb-4">Типы контента</div>
        <div className="space-y-3">
          <StatBar label="Текстовые сообщения" value={72} color="cyan" />
          <StatBar label="Фото и видео" value={18} color="violet" />
          <StatBar label="Голосовые" value={6} color="green" />
          <StatBar label="Стикеры и GIF" value={4} color="orange" />
        </div>
      </div>

      <div className="glass rounded-xl p-5 border border-border">
        <div className="text-xs text-muted-foreground uppercase tracking-widest mb-3">Топ активных часов</div>
        <ActivityChart />
      </div>

      <div className="glass rounded-xl p-4 border border-emerald-500/20">
        <div className="flex items-center gap-2 mb-3">
          <Icon name="TrendingUp" size={14} className="text-emerald-400" />
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Системы онлайн</span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {["Кэш Redis", "Webhook API", "Уведомления"].map((t, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs text-foreground/70">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />
              {t}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SegmentsSection() {
  const segments = [
    { name: "Лидеры мнений", count: 1240, tag: "KOL", color: "cyan", desc: "Высокая активность, >5K подп.", pct: 8 },
    { name: "Активные читатели", count: 18400, tag: "Active", color: "violet", desc: "Регулярные просмотры", pct: 62 },
    { name: "Молчуны", count: 7200, tag: "Lurker", color: "green", desc: "Читают, не пишут", pct: 24 },
    { name: "Боты и спамеры", count: 1800, tag: "Bot", color: "orange", desc: "Автоматическое поведение", pct: 6 },
  ];
  const filters = ["Язык", "Активность", "Геолокация", "Тематика", "Дата рег."];

  return (
    <div className="space-y-4 animate-fade-up-1">
      <div className="glass rounded-xl p-4 border border-border">
        <div className="flex items-center gap-2 mb-3">
          <Icon name="Filter" size={13} className="text-orange-400" />
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Фильтры аудитории</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {filters.map(f => (
            <button key={f} className="text-xs px-2 py-0.5 rounded-full font-medium bg-secondary text-foreground/70 border border-border hover:border-orange-500/40 hover:text-orange-400 transition-all">
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {segments.map((s, i) => {
          const c = COLOR_MAP[s.color];
          const barColor = s.color === "cyan" ? "hsl(195,100%,50%)" : s.color === "violet" ? "hsl(270,80%,65%)" : s.color === "green" ? "hsl(142,80%,50%)" : "hsl(32,100%,55%)";
          return (
            <div key={i} className={`glass glass-hover rounded-xl p-4 border ${c.border}`}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-semibold text-foreground">{s.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${c.bg} ${c.text} border ${c.border}`}>{s.tag}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">{s.desc}</div>
                </div>
                <div className="text-right">
                  <div className={`text-lg font-display font-bold ${c.text}`}>{s.count.toLocaleString()}</div>
                  <div className="text-[10px] text-muted-foreground">{s.pct}%</div>
                </div>
              </div>
              <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${s.pct}%`, background: barColor }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ExportSection() {
  const formats = [
    { ext: "CSV", desc: "Таблица данных", color: "green", size: "~2.4 MB" },
    { ext: "JSON", desc: "Сырые данные API", color: "cyan", size: "~3.1 MB" },
    { ext: "PDF", desc: "Готовый отчёт", color: "violet", size: "~1.8 MB" },
  ];

  return (
    <div className="space-y-4 animate-fade-up-1">
      <div className="glass rounded-xl p-5 border border-border">
        <div className="flex items-center gap-2 mb-4">
          <Icon name="Settings2" size={14} className="text-cyan-400" />
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Параметры экспорта</span>
        </div>
        <div className="space-y-3">
          <div>
            <div className="text-xs text-muted-foreground mb-1">Диапазон дат</div>
            <select className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-cyan-500/50">
              <option>Последние 30 дней</option>
              <option>Последние 90 дней</option>
              <option>Весь период</option>
            </select>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1">Фильтр по активности</div>
            <select className="w-full bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-cyan-500/50">
              <option>Все пользователи</option>
              <option>Активные</option>
              <option>Неактивные</option>
            </select>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-2">Включить поля</div>
            <div className="grid grid-cols-2 gap-1.5">
              {["Имя", "Username", "ID", "Чаты", "Активность", "Медиа"].map(f => (
                <label key={f} className="flex items-center gap-2 text-xs text-foreground/80 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded accent-cyan-400" />
                  {f}
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs text-muted-foreground px-1">Выберите формат</div>
        {formats.map((f, i) => {
          const c = COLOR_MAP[f.color];
          return (
            <div key={i} className={`glass glass-hover rounded-xl p-4 border ${c.border} flex items-center gap-3 cursor-pointer`}>
              <div className={`w-10 h-10 rounded-xl ${c.bg} border ${c.border} flex items-center justify-center`}>
                <span className={`text-xs font-display font-bold ${c.text}`}>{f.ext}</span>
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-foreground">{f.ext} файл</div>
                <div className="text-xs text-muted-foreground">{f.desc} · {f.size}</div>
              </div>
              <Icon name="Download" size={14} className={c.text} />
            </div>
          );
        })}
      </div>

      <div className="glass rounded-xl p-4 border border-emerald-500/20">
        <div className="flex items-center gap-2 mb-3">
          <Icon name="Bell" size={13} className="text-emerald-400" />
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Уведомления</span>
        </div>
        <div className="space-y-2">
          {["Экспорт готов", "Новые данные", "Изменение профиля"].map(n => (
            <label key={n} className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-foreground/80">{n}</span>
              <input type="checkbox" defaultChecked className="accent-emerald-400 w-4 h-4" />
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

function HelpSection() {
  const [open, setOpen] = useState<number | null>(null);
  const faqs = [
    { q: "Какие данные анализирует FunStat?", a: "Только публичные данные: сообщения в открытых чатах, каналах и группах. Приватные переписки недоступны." },
    { q: "Как работает кэширование?", a: "Результаты запросов кэшируются на 24 часа. Это ускоряет повторные запросы и снижает нагрузку на серверы." },
    { q: "Какие форматы экспорта доступны?", a: "CSV, JSON и PDF. Каждый формат подходит для разных задач: CSV для таблиц, JSON для разработчиков, PDF для отчётов." },
    { q: "Как настроить уведомления?", a: "В разделе Экспорт → Уведомления. Доступны оповещения о готовности экспорта, новых данных и изменениях профиля." },
    { q: "Безопасно ли использовать FunStat?", a: "Все запросы обрабатываются анонимно. Личные данные пользователя не сохраняются и не передаются третьим лицам." },
  ];

  return (
    <div className="space-y-4 animate-fade-up-1">
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Документация", icon: "BookOpen", color: "cyan" },
          { label: "Поддержка", icon: "MessageCircle", color: "violet" },
          { label: "API Docs", icon: "Code2", color: "green" },
        ].map((item, i) => {
          const c = COLOR_MAP[item.color];
          return (
            <button key={i} className={`glass glass-hover rounded-xl p-4 border ${c.border} flex flex-col items-center gap-2`}>
              <Icon name={item.icon} size={20} className={c.text} />
              <span className="text-xs text-foreground/70">{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="glass rounded-xl p-5 border border-border">
        <div className="flex items-center gap-2 mb-4">
          <Icon name="HelpCircle" size={14} className="text-cyan-400" />
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Частые вопросы</span>
        </div>
        <div className="space-y-2">
          {faqs.map((faq, i) => (
            <div key={i} className="border border-border rounded-lg overflow-hidden">
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between p-3 text-left hover:bg-secondary/50 transition-colors"
              >
                <span className="text-sm text-foreground/90 pr-2">{faq.q}</span>
                <Icon name="ChevronDown" size={14} className={`text-muted-foreground flex-shrink-0 transition-transform duration-200 ${open === i ? "rotate-180" : ""}`} />
              </button>
              {open === i && (
                <div className="px-3 pb-3 text-sm text-muted-foreground leading-relaxed border-t border-border pt-3 animate-fade-in">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="glass rounded-xl p-5 border border-violet-500/20">
        <div className="flex items-center gap-2 mb-3">
          <Icon name="Send" size={14} className="text-violet-400" />
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Написать в поддержку</span>
        </div>
        <div className="space-y-2">
          <input
            placeholder="Ваш вопрос..."
            className="w-full bg-secondary border border-border rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-violet-500/50 transition-colors"
          />
          <button className="w-full py-2.5 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90"
            style={{ background: "hsl(270,80%,65%)" }}>
            Отправить
          </button>
        </div>
      </div>
    </div>
  );
}

const SECTION_COMPONENTS: Record<Section, React.FC> = {
  analysis: AnalysisSection,
  search: SearchSection,
  stats: StatsSection,
  segments: SegmentsSection,
  export: ExportSection,
  help: HelpSection,
};

export default function Index() {
  const [active, setActive] = useState<Section>("analysis");
  const ActiveComponent = SECTION_COMPONENTS[active];

  return (
    <div className="min-h-screen bg-background grid-pattern scanline">
      {/* Header */}
      <header className="sticky top-0 z-50 glass border-b border-border">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, hsl(195,100%,50%), hsl(270,80%,65%))" }}>
              <Icon name="ScanSearch" size={16} className="text-background" />
            </div>
            <div>
              <div className="font-display font-bold text-base leading-none glow-text-cyan" style={{ color: "hsl(195,100%,50%)" }}>
                FunStat
              </div>
              <div className="text-[9px] text-muted-foreground uppercase tracking-widest leading-none mt-0.5">Telegram Analytics</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />
              Online
            </div>
            <button className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center hover:bg-secondary/80 transition-colors">
              <Icon name="Bell" size={14} className="text-muted-foreground" />
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-lg mx-auto px-4 py-5 pb-28">
        <ActiveComponent key={active} />
      </main>

      {/* Bottom Nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 glass border-t border-border">
        <div className="max-w-lg mx-auto px-2 py-2">
          <div className="grid grid-cols-6 gap-0.5">
            {NAV_ITEMS.map(item => {
              const isActive = active === item.id;
              const c = COLOR_MAP[item.color];
              return (
                <button
                  key={item.id}
                  onClick={() => setActive(item.id)}
                  className={`flex flex-col items-center gap-1 py-2 px-1 rounded-xl transition-all duration-200 ${
                    isActive ? `${c.bg} ${c.text}` : "text-muted-foreground hover:text-foreground/70"
                  }`}
                >
                  <Icon name={item.icon} size={18} />
                  <span className="text-[9px] font-medium">{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>
    </div>
  );
}