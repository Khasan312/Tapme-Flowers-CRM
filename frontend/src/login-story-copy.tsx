import { Fragment, type CSSProperties } from "react";

function WrittenLine({
  text,
  delay,
  pace,
}: {
  text: string;
  delay: number;
  pace: number;
}) {
  let elapsed = delay;

  return text.split(" ").map((word, index) => {
    const duration = word.length * pace;
    const style = {
      "--write-delay": `${elapsed}ms`,
      "--write-duration": `${duration}ms`,
    } as CSSProperties;
    elapsed += duration + pace;

    return (
      <Fragment key={index}>
        {index > 0 && " "}
        <span className="login-story-word" style={style}>
          {word}
        </span>
      </Fragment>
    );
  });
}

export function LoginStoryCopy() {
  return (
    <div>
      <span className="eyebrow">
        <WrittenLine text="КАЖДЫЙ БУКЕТ — ВАЖЕН" delay={160} pace={22} />
      </span>
      <h1>
        <WrittenLine text="Больше внимания" delay={650} pace={27} />
        <br /> <WrittenLine text="цветам и людям." delay={1110} pace={27} />
      </h1>
      <p>
        <WrittenLine
          text="Заказы, клиенты и команда вашего магазина"
          delay={1570}
          pace={16}
        />
        <br />{" "}
        <WrittenLine
          text="в одном рабочем пространстве."
          delay={2270}
          pace={16}
        />
      </p>
    </div>
  );
}
