import { useState } from "react";
import { ImageIcon } from "lucide-react";
import { Modal } from "./components";

export function ProductPhoto({ url, name }: { url?: string; name: string }) {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState("");
  if (!url || failed === url)
    return (
      <span
        className="product-photo-placeholder"
        aria-hidden="true"
        title="Фото не добавлено"
      >
        <ImageIcon size={20} />
      </span>
    );
  return (
    <>
      <button
        type="button"
        className="product-photo-button"
        aria-label={`Посмотреть фото ${name}`}
        onClick={() => setOpen(true)}
      >
        <img
          src={url}
          alt={name}
          loading="lazy"
          onError={() => setFailed(url)}
        />
      </button>
      {open && (
        <Modal title={`Фото: ${name}`} close={() => setOpen(false)}>
          <div className="modal-body">
            <img className="product-photo-full" src={url} alt={name} />
          </div>
        </Modal>
      )}
    </>
  );
}
