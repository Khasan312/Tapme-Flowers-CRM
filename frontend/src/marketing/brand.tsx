import { siteUrl } from "./routes";

export function BrandBadge({
  size,
  className,
}: {
  size: number;
  className?: string;
}) {
  return (
    <img
      className={className}
      src={siteUrl("favicon.svg")}
      width={size}
      height={size}
      alt=""
    />
  );
}
