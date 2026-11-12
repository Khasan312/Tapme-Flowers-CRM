import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Bell,
  BookOpen,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  Headphones,
  Layers3,
  Menu,
  MessageCircle,
  Play,
  Plus,
  Sparkles,
  Store,
  Truck,
  X,
  type LucideIcon,
} from "lucide-react";
import { BrandBadge } from "./brand";
import {
  features,
  guides,
  legalLinks,
  operator,
  questions,
  solutions,
} from "./content";
import { ProductDemo } from "./demo";
import { legalDocuments } from "./legal";
import { siteUrl } from "./routes";
import "./site.css";
import "./demo.css";

type Link = { path: string; label: string };

const navigation = [
  {
    label: "Продукт",
    links: [
      { path: "product", label: "Возможности" },
      { path: "demo", label: "Интерактивное демо" },
      ...features.map((item) => ({
        path: `product/${item.id}`,
        label: item.title,
      })),
    ],
  },
  {
    label: "Решения",
    links: [
      { path: "solutions", label: "Все решения" },
      ...solutions.map((item) => ({
        path: `solutions/${item.id}`,
        label: item.title,
      })),
    ],
  },
  { label: "Компания", links: [{ path: "company", label: "О Tapme Flowers" }] },
  {
    label: "Помощь",
    links: [
      { path: "help", label: "База знаний" },
      { path: "faq", label: "Частые вопросы" },
      { path: "support", label: "Поддержка" },
    ],
  },
];

const titles: Record<string, string> = {
  product: "Возможности",
  solutions: "Решения",
  company: "О компании",
  help: "База знаний",
  support: "Поддержка",
  faq: "Частые вопросы",
  demo: "Интерактивное демо",
};
const icons = [MessageCircle, ClipboardList, Truck, Bell];
const solutionIcons = [BrandBadge, Store, Layers3];
const guideIcons = [CircleHelp, MessageCircle, ClipboardList, Truck];
const HEADER_CONDENSE_SCROLL_Y = 24;
const DESKTOP_HEADER_HOVER = "(width > 980px) and (any-hover: hover)";

function SiteLink({ link, current }: { link: Link; current?: string }) {
  return (
    <a
      href={siteUrl(link.path)}
      aria-current={current === link.path ? "page" : undefined}
    >
      {link.label}
    </a>
  );
}

function Logo() {
  return (
    <a className="mk-logo" href={siteUrl()} aria-label="Tapme Flowers, главная">
      <BrandBadge className="mk-logo-mark" size={34} />
      <span>
        tapme <b>Flowers</b>
      </span>
    </a>
  );
}

function Header({ path }: { path: string }) {
  const [condensed, setCondensed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openGroup, setOpenGroup] = useState<{
    index: number;
    fromHover: boolean;
  } | null>(null);
  const header = useRef<HTMLElement>(null);
  const nav = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const groupButtons = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    function syncHeader() {
      setCondensed(window.scrollY > HEADER_CONDENSE_SCROLL_Y);
    }

    syncHeader();
    window.addEventListener("scroll", syncHeader, { passive: true });
    return () => window.removeEventListener("scroll", syncHeader);
  }, []);

  useEffect(() => {
    function closeOutside(event: PointerEvent) {
      if (!header.current?.contains(event.target as Node)) {
        setOpenGroup(null);
        setMobileOpen(false);
      }
    }
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, []);

  useEffect(() => {
    if (mobileOpen) nav.current?.querySelector("a")?.focus();
  }, [mobileOpen]);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key !== "Escape" || event.defaultPrevented) return;

      const focusInHeader = header.current?.contains(document.activeElement);
      if (openGroup) {
        if (focusInHeader) groupButtons.current[openGroup.index]?.focus();
        setOpenGroup(null);
      } else if (mobileOpen) {
        if (focusInHeader) menuButton.current?.focus();
        setMobileOpen(false);
      }
    }

    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [mobileOpen, openGroup]);

  return (
    <header
      className={`mk-header${condensed ? " is-condensed" : ""}`}
      ref={header}
    >
      <div className="mk-header-inner">
        <Logo />
        <nav
          id="site-navigation"
          ref={nav}
          className={`mk-nav${mobileOpen ? " is-open" : ""}`}
          aria-label="Основная навигация"
        >
          <SiteLink link={{ path: "", label: "Главная" }} current={path} />
          {navigation.map(({ label, links }, index) => {
            const isOpen = openGroup?.index === index;

            function closeHoverMenu() {
              setOpenGroup((current) =>
                current?.index === index && current.fromHover ? null : current,
              );
            }

            return (
              <div
                className="mk-nav-group"
                key={label}
                onPointerEnter={(event) => {
                  if (
                    event.pointerType === "mouse" &&
                    window.matchMedia(DESKTOP_HEADER_HOVER).matches &&
                    !document.activeElement?.closest(".mk-nav-group ul")
                  ) {
                    setOpenGroup((current) =>
                      current?.index === index
                        ? current
                        : { index, fromHover: true },
                    );
                  }
                }}
                onPointerLeave={(event) => {
                  if (!event.currentTarget.contains(document.activeElement)) {
                    closeHoverMenu();
                  }
                }}
                onBlur={(event) => {
                  if (
                    !event.currentTarget.contains(event.relatedTarget) &&
                    !event.currentTarget.matches(":hover")
                  ) {
                    closeHoverMenu();
                  }
                }}
              >
                <button
                  type="button"
                  ref={(node) => {
                    groupButtons.current[index] = node;
                  }}
                  aria-expanded={isOpen}
                  aria-controls={`site-menu-${index}`}
                  onClick={() =>
                    setOpenGroup((current) =>
                      current?.index === index && !current.fromHover
                        ? null
                        : { index, fromHover: false },
                    )
                  }
                >
                  {label}
                  <ChevronDown size={13} aria-hidden="true" />
                </button>
                <ul id={`site-menu-${index}`} inert={!isOpen}>
                  {links.map((link) => (
                    <li key={link.path}>
                      <SiteLink link={link} current={path} />
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
          <a className="mk-mobile-demo" href={siteUrl("demo")}>
            Попробовать демо
          </a>
        </nav>
        <div className="mk-header-actions">
          <a className="mk-login" href={siteUrl("login")}>
            Войти
          </a>
          <a
            className="mk-btn mk-btn-dark mk-header-demo"
            href={siteUrl("demo")}
          >
            Попробовать <ArrowUpRight size={15} aria-hidden="true" />
          </a>
          <button
            className="mk-menu-toggle"
            type="button"
            ref={menuButton}
            aria-label={mobileOpen ? "Закрыть меню" : "Открыть меню"}
            aria-expanded={mobileOpen}
            aria-controls="site-navigation"
            onClick={() => {
              setMobileOpen(!mobileOpen);
              setOpenGroup(null);
            }}
          >
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="mk-footer">
      <div className="mk-wrap">
        <div className="mk-footer-main">
          <div className="mk-footer-brand">
            <Logo />
            <p>
              Заказы, клиенты и команда цветочного магазина в одном рабочем
              пространстве.
            </p>
          </div>
          {navigation.map(({ label, links }) => (
            <div key={label}>
              <h2>{label}</h2>
              <ul>
                {links.map((link) => (
                  <li key={link.path}>
                    <SiteLink link={link} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mk-footer-bottom">
          <span>
            © {new Date().getFullYear()} Tapme Flowers · {operator.name} ·{" "}
            <a href={operator.phoneHref}>{operator.phone}</a> ·{" "}
            <a href={`mailto:${operator.supportEmail}`}>
              {operator.supportEmail}
            </a>
          </span>
          <nav aria-label="Правовая информация">
            {legalLinks.map((link) => (
              <a key={link.path} href={siteUrl(link.path)}>
                {link.label}
              </a>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  );
}

function Card({
  title,
  description,
  path,
  icon: Icon,
}: {
  title: string;
  description: string;
  path: string;
  icon: LucideIcon | typeof BrandBadge;
}) {
  return (
    <a className="mk-card" href={siteUrl(path)}>
      <span className="mk-card-icon">
        <Icon size={21} aria-hidden="true" />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      <ArrowUpRight className="mk-card-arrow" size={19} aria-hidden="true" />
    </a>
  );
}

function FAQ({ limit = questions.length }: { limit?: number }) {
  return (
    <div className="mk-faq-list">
      {questions.slice(0, limit).map(({ title, answer }) => (
        <details key={title}>
          <summary>
            {title}
            <Plus size={19} aria-hidden="true" />
          </summary>
          <p>{answer}</p>
        </details>
      ))}
    </div>
  );
}

function CTA({ animated = false }: { animated?: boolean }) {
  const panel = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const element = panel.current;
    if (!animated || !element) return;

    const observer = new IntersectionObserver(([entry]) => {
      setInView(entry.isIntersecting);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [animated]);

  return (
    <section className="mk-wrap mk-section">
      <div
        ref={panel}
        className={`mk-cta${animated ? " is-animated" : ""}${inView ? " is-in-view" : ""}`}
      >
        <span className="mk-kicker">
          <BrandBadge size={15} /> TAPME FLOWERS
        </span>
        <h2>Посмотрите, как заказ проходит от чата до доставки</h2>
        <p>Откройте пример и попробуйте оформить букет из переписки.</p>
        <a className="mk-btn mk-btn-dark" href={siteUrl("demo")}>
          Открыть демо <ArrowUpRight size={17} aria-hidden="true" />
        </a>
      </div>
    </section>
  );
}

function Home() {
  return (
    <>
      <section className="mk-hero">
        <div className="mk-wrap">
          <span className="mk-kicker">
            <Sparkles size={15} /> CRM ДЛЯ ЦВЕТОЧНЫХ МАГАЗИНОВ
          </span>
          <h1>
            От первого сообщения
            <br /> <em>до вручения букета</em>
          </h1>
          <p>
            Переписка, заказы и доставки в одном месте. Для менеджеров,
            флористов и курьеров вашей команды.
          </p>
          <div className="mk-actions">
            <a className="mk-btn mk-btn-dark" href={siteUrl("demo")}>
              <Play size={16} aria-hidden="true" /> Попробовать демо
            </a>
            <a className="mk-btn mk-btn-light" href="#product-demo">
              Как это работает <ArrowDown size={16} aria-hidden="true" />
            </a>
          </div>
          <div id="product-demo">
            <ProductDemo />
          </div>
        </div>
      </section>
      <section className="mk-wrap mk-section">
        <div className="mk-section-head">
          <span className="mk-kicker">ПРОДУКТ</span>
          <h2>Всё, что нужно для работы с заказом</h2>
          <p>
            Отвечайте в чатах, оформляйте букеты и передавайте их в доставку.
          </p>
        </div>
        <div className="mk-grid">
          {features.map((item, i) => (
            <Card
              key={item.id}
              {...item}
              icon={icons[i]}
              path={`product/${item.id}`}
            />
          ))}
        </div>
      </section>
      <section className="mk-band">
        <div className="mk-wrap mk-section">
          <div className="mk-section-head">
            <span className="mk-kicker">РЕШЕНИЯ</span>
            <h2>Для одного магазина и для сети</h2>
            <p>Выберите сценарий, который ближе вашему бизнесу.</p>
          </div>
          <div className="mk-grid mk-grid-three">
            {solutions.map((item, i) => (
              <Card
                key={item.id}
                {...item}
                icon={solutionIcons[i]}
                path={`solutions/${item.id}`}
              />
            ))}
          </div>
        </div>
      </section>
      <section
        className="mk-wrap mk-section mk-faq-section mk-faq-home"
        aria-labelledby="home-faq-title"
      >
        <div className="mk-section-head">
          <span className="mk-kicker">ПОМОЩЬ</span>
          <h2 id="home-faq-title">Частые вопросы</h2>
          <p>
            Как попробовать CRM без аккаунта, подключить WhatsApp и Instagram и
            дать доступ команде.
          </p>
          <a className="mk-text-link" href={siteUrl("faq")}>
            Все вопросы <ArrowRight size={17} aria-hidden="true" />
          </a>
        </div>
        <FAQ limit={5} />
        <a className="mk-faq-contact" href={siteUrl("support")}>
          <span className="mk-faq-contact-icon">
            <Headphones size={19} aria-hidden="true" />
          </span>
          <span>
            <strong>Не нашли ответ?</strong>
            <span>Перейти в поддержку</span>
          </span>
          <ArrowUpRight size={18} aria-hidden="true" />
        </a>
      </section>
      <CTA animated />
    </>
  );
}

function Intro({
  kicker,
  title,
  description,
  children,
}: {
  kicker: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <section className="mk-intro">
      <div className="mk-wrap">
        <span className="mk-kicker">{kicker}</span>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
        {children}
      </div>
    </section>
  );
}

function DemoLink() {
  return (
    <a className="mk-btn mk-btn-dark" href={siteUrl("demo")}>
      Попробовать демо <ArrowUpRight size={17} aria-hidden="true" />
    </a>
  );
}

function Subpage({ path }: { path: string }) {
  const [group, detail] = path.split("/");
  const feature = features.find((item) => path === `product/${item.id}`);
  const solution = solutions.find((item) => path === `solutions/${item.id}`);
  const guide = guides.find((item) => path === `help/${item.id}`);
  const item = feature ?? solution ?? guide;
  const document = Object.hasOwn(legalDocuments, path)
    ? legalDocuments[path]
    : undefined;

  if (document)
    return (
      <>
        <Intro kicker="ПРАВОВАЯ ИНФОРМАЦИЯ" title={document.title} />
        <article className="mk-wrap mk-section mk-article">
          <p className="mk-legal-notice">{document.notice}</p>
          <nav className="mk-legal-toc" aria-label="Содержание">
            {document.sections.map(({ title }, i) => (
              <a key={title} href={`#section-${i + 1}`}>
                {title}
              </a>
            ))}
          </nav>
          {document.sections.map(({ title, paragraphs }, i) => (
            <section id={`section-${i + 1}`} key={title}>
              <h2>{title}</h2>
              {paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </section>
          ))}
          <nav className="mk-related" aria-label="Другие документы">
            {legalLinks
              .filter((link) => link.path !== path)
              .map((link) => (
                <a key={link.path} href={siteUrl(link.path)}>
                  {link.label}
                </a>
              ))}
          </nav>
        </article>
      </>
    );

  if (item) {
    const steps = guide?.steps ?? feature?.points ?? solution?.points ?? [];
    const parent =
      group === "help"
        ? "База знаний"
        : group === "solutions"
          ? "Все решения"
          : "Все возможности";
    return (
      <>
        <Intro
          kicker={
            group === "help"
              ? "БАЗА ЗНАНИЙ"
              : group === "solutions"
                ? "РЕШЕНИЯ"
                : "ПРОДУКТ"
          }
          title={item.title}
          description={item.description}
        />
        <div className="mk-wrap mk-section mk-article">
          <a className="mk-text-link" href={siteUrl(group)}>
            <ArrowLeft size={17} /> {parent}
          </a>
          <h2>{guide ? "Пошаговая инструкция" : "Как это работает"}</h2>
          <ol className="mk-steps">
            {steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          {guide ? (
            <a className="mk-btn mk-btn-dark" href={siteUrl("login")}>
              Войти в CRM <ArrowUpRight size={17} />
            </a>
          ) : (
            <DemoLink />
          )}
        </div>
      </>
    );
  }

  if (path === "product" || path === "solutions" || path === "help") {
    const isProduct = path === "product";
    const isHelp = path === "help";
    const items = isProduct ? features : isHelp ? guides : solutions;
    const cardIcons = isProduct ? icons : isHelp ? guideIcons : solutionIcons;
    return (
      <>
        <Intro
          kicker={isProduct ? "ПРОДУКТ" : isHelp ? "ПОМОЩЬ" : "РЕШЕНИЯ"}
          title={
            isProduct
              ? "Рабочее пространство цветочного магазина"
              : isHelp
                ? "База знаний"
                : "Решения для цветочного бизнеса"
          }
          description={
            isProduct
              ? "Инструменты для команды, которая принимает заказы, собирает букеты и доставляет их."
              : isHelp
                ? "Короткие инструкции по входу, настройке каналов и первым заказам."
                : "От небольшой студии до магазина с несколькими филиалами."
          }
        />
        <section className="mk-wrap mk-section">
          <div
            className={`mk-grid${path === "solutions" ? " mk-grid-three" : ""}`}
          >
            {items.map((entry, i) => (
              <Card
                key={entry.id}
                {...entry}
                icon={cardIcons[i]}
                path={`${path}/${entry.id}`}
              />
            ))}
          </div>
        </section>
        {isHelp ? (
          <section className="mk-wrap mk-section mk-faq-section">
            <div className="mk-section-head">
              <h2>Частые вопросы</h2>
              <a className="mk-text-link" href={siteUrl("support")}>
                Поддержка <ArrowRight size={17} />
              </a>
            </div>
            <FAQ />
          </section>
        ) : (
          <CTA />
        )}
      </>
    );
  }

  if (path === "demo")
    return (
      <>
        <Intro
          kicker="ИНТЕРАКТИВНОЕ ДЕМО"
          title="Попробуйте Tapme Flowers"
          description="Откройте сообщение, соберите черновик заказа и посмотрите, как выглядит доставка."
        />
        <section className="mk-wrap mk-demo-page">
          <ProductDemo />
        </section>
      </>
    );

  if (path === "faq")
    return (
      <>
        <Intro
          kicker="ПОМОЩЬ"
          title="Частые вопросы"
          description="Ответы про доступ, подключение каналов и работу с заказами."
        />
        <section className="mk-wrap mk-section mk-article">
          <FAQ />
          <a className="mk-text-link" href={siteUrl("support")}>
            Перейти в поддержку <ArrowRight size={17} />
          </a>
        </section>
      </>
    );

  if (path === "support")
    return (
      <>
        <Intro
          kicker="ПОМОЩЬ"
          title="Поддержка"
          description="Выберите, с чем нужна помощь. По вопросам учётной записи и прав доступа обратитесь к владельцу магазина."
        />
        <section className="mk-wrap mk-section">
          <div className="mk-grid">
            <Card
              title="Не получается войти"
              description="Проверьте, как получить логин и восстановить доступ."
              path="help/access"
              icon={Headphones}
            />
            <Card
              title="Не приходят сообщения"
              description="Проверьте настройки WhatsApp или Instagram."
              path="help/channels"
              icon={MessageCircle}
            />
            <Card
              title="Вопрос по заказу или доставке"
              description="Узнайте, как открыть ссылку отслеживания. По конкретному заказу свяжитесь с магазином по контактам на этой ссылке."
              path="help/tracking"
              icon={Truck}
            />
            <Card
              title="Другой вопрос"
              description="Посмотрите частые вопросы или откройте базу знаний."
              path="faq"
              icon={BookOpen}
            />
          </div>
        </section>
      </>
    );

  if (path === "company")
    return (
      <>
        <Intro
          kicker="КОМПАНИЯ"
          title="О Tapme Flowers"
          description="Мы создаём CRM для цветочных магазинов в Кыргызстане."
        />
        <section className="mk-wrap mk-section mk-article">
          <h2>Зачем мы делаем Tapme Flowers</h2>
          <p>
            Цветочный заказ может начаться в WhatsApp, измениться в Instagram и
            закончиться у двери получателя. Мы собрали переписку, состав заказа,
            оплату и доставку в одном рабочем пространстве, чтобы детали
            оставались с заказом на каждом этапе.
          </p>
          <h2>Для всей команды</h2>
          <p>
            Менеджер оформляет заказ, флорист видит, что собрать, а курьер
            получает данные для доставки. Владелец может распределить доступы по
            ролям и филиалам.
          </p>
          <a className="mk-text-link" href={siteUrl("product")}>
            Посмотреть продукт <ArrowRight size={17} />
          </a>
        </section>
        <CTA />
      </>
    );

  return (
    <Intro
      kicker="TAPME FLOWERS"
      title="Страница не найдена"
      description={
        detail
          ? "Откройте нужный раздел с главной страницы."
          : "Проверьте адрес или вернитесь на главную."
      }
    >
      <div className="mk-actions">
        <a className="mk-btn mk-btn-dark" href={siteUrl()}>
          На главную <ArrowRight size={17} />
        </a>
      </div>
    </Intro>
  );
}

export function MarketingSite({ path }: { path: string }) {
  useEffect(() => {
    const isLegal = Object.hasOwn(legalDocuments, path);
    const title =
      (isLegal ? legalDocuments[path].title : undefined) ??
      (Object.hasOwn(titles, path) ? titles[path] : undefined) ??
      features.find(({ id }) => path === `product/${id}`)?.title ??
      solutions.find(({ id }) => path === `solutions/${id}`)?.title ??
      guides.find(({ id }) => path === `help/${id}`)?.title;
    document.title = title
      ? `${title} · Tapme Flowers`
      : "Tapme Flowers — CRM для цветочных магазинов";
    if (isLegal) {
      const robots = document.createElement("meta");
      robots.name = "robots";
      robots.content = "noindex";
      document.head.append(robots);
      return () => robots.remove();
    }
  }, [path]);

  return (
    <div className="mk">
      <a className="mk-skip" href="#site-content">
        Перейти к содержимому
      </a>
      <Header path={path} />
      <main id="site-content" tabIndex={-1}>
        {path ? <Subpage path={path} /> : <Home />}
      </main>
      <Footer />
    </div>
  );
}
