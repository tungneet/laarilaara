"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { SectionCard } from "@/components/profile-editor/section-card";
import {
  useDeleteProfileMedia,
  useMediaAsset,
  useProfileMedia,
  useUpdateProfileMedia,
  useUploadProfilePhoto,
  type PhotoVisibility,
  type ProfileMedia,
  type UploadStage,
} from "@/lib/media";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_FILE_SIZE = 20 * 1024 * 1024;

const VISIBILITY_OPTIONS: Array<{ value: PhotoVisibility; label: string }> = [
  { value: "public", label: "Everyone" },
  { value: "connections_only", label: "Connections only" },
  { value: "managers_only", label: "Profile managers only" },
];

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong.";
}

function ExistingPhoto({ profileId, photo }: { profileId: string; photo: ProfileMedia }) {
  const asset = useMediaAsset(photo.asset_id);
  const update = useUpdateProfileMedia(profileId);
  const remove = useDeleteProfileMedia(profileId);
  const [caption, setCaption] = useState(photo.caption ?? "");
  const [confirmingRemove, setConfirmingRemove] = useState(false);
  const imageUrl = asset.data?.download_url;

  return (
    <li className="min-w-0">
      <div className="relative aspect-[4/5] overflow-hidden rounded-lg border border-glass-line bg-white/5">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={photo.caption || "Profile photo"}
            fill
            sizes="(min-width: 1280px) 240px, (min-width: 640px) 40vw, 90vw"
            unoptimized
            className="object-cover"
          />
        ) : (
          <div className="grid h-full place-items-center text-[12px] text-ink-soft">
            {asset.isLoading ? "Loading photo…" : "Photo unavailable"}
          </div>
        )}
        {photo.is_primary && (
          <span className="bg-gradient-brand absolute top-2 left-2 rounded-full px-2.5 py-1 text-[10.5px] font-semibold text-on-primary">
            Primary
          </span>
        )}
      </div>

      <div className="mt-3 space-y-2.5">
        <label className="block text-[12px] font-medium text-ink-soft">
          Caption
          <input
            value={caption}
            onChange={(event) => setCaption(event.target.value)}
            maxLength={300}
            placeholder="Optional caption"
            className="mt-1 w-full rounded-lg border border-glass-line bg-white/5 px-3 py-2 text-[13px] text-ink outline-none placeholder:text-ink-soft/50 focus:border-primary"
          />
        </label>
        <label className="block text-[12px] font-medium text-ink-soft">
          Visible to
          <select
            value={photo.visibility ?? "public"}
            disabled={update.isPending}
            onChange={(event) =>
              update.mutate({
                mediaId: photo.id,
                updates: { visibility: event.target.value as PhotoVisibility },
              })
            }
            className="mt-1 w-full rounded-lg border border-glass-line bg-[var(--bg-a)] px-3 py-2 text-[13px] text-ink outline-none focus:border-primary"
          >
            {VISIBILITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        {(update.isError || remove.isError) && (
          <p role="alert" className="text-[12px] text-accent">
            {errorMessage(update.error ?? remove.error)}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          {caption !== (photo.caption ?? "") && (
            <button
              type="button"
              disabled={update.isPending}
              onClick={() => update.mutate({ mediaId: photo.id, updates: { caption: caption.trim() || null } })}
              className="cursor-pointer rounded-full bg-primary-soft px-3.5 py-1.5 text-[12px] font-semibold disabled:opacity-60"
            >
              Save caption
            </button>
          )}
          {!photo.is_primary && (
            <button
              type="button"
              disabled={update.isPending}
              onClick={() => update.mutate({ mediaId: photo.id, updates: { is_primary: true } })}
              className="cursor-pointer rounded-full border border-glass-line px-3.5 py-1.5 text-[12px] font-semibold hover:border-primary disabled:opacity-60"
            >
              Make primary
            </button>
          )}
          {confirmingRemove ? (
            <>
              <button
                type="button"
                disabled={remove.isPending}
                onClick={() => remove.mutate({ mediaId: photo.id, assetId: photo.asset_id })}
                className="cursor-pointer rounded-full bg-accent-soft px-3.5 py-1.5 text-[12px] font-semibold disabled:opacity-60"
              >
                {remove.isPending ? "Removing…" : "Confirm remove"}
              </button>
              <button type="button" onClick={() => setConfirmingRemove(false)} className="cursor-pointer px-2 text-[12px] text-ink-soft">
                Cancel
              </button>
            </>
          ) : (
            <button type="button" onClick={() => setConfirmingRemove(true)} className="cursor-pointer px-2 text-[12px] text-ink-soft hover:text-ink">
              Remove
            </button>
          )}
        </div>
      </div>
    </li>
  );
}

export function PhotosPanel({ profileId }: { profileId: string }) {
  const media = useProfileMedia(profileId);
  const upload = useUploadProfilePhoto(profileId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [visibility, setVisibility] = useState<PhotoVisibility>("public");
  const [makePrimary, setMakePrimary] = useState(false);
  const [stage, setStage] = useState<UploadStage | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const photos = media.data ?? [];

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function selectFile(nextFile: File | undefined) {
    setFileError(null);
    if (!nextFile) return;
    if (!ACCEPTED_TYPES.includes(nextFile.type)) {
      setFileError("Choose a JPEG, PNG, or WebP image.");
      return;
    }
    if (nextFile.size > MAX_FILE_SIZE) {
      setFileError("Photo must be 20 MB or smaller.");
      return;
    }
    setFile(nextFile);
    setPreviewUrl(URL.createObjectURL(nextFile));
    setMakePrimary(photos.length === 0);
  }

  function resetForm() {
    setFile(null);
    setCaption("");
    setVisibility("public");
    setMakePrimary(false);
    setStage(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <SectionCard
      title="Profile photos"
      description="Add clear, recent photos and decide who can see each one."
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,280px)_1fr]">
        <div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(",")}
            className="sr-only"
            onChange={(event) => selectFile(event.target.files?.[0])}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="group relative grid aspect-[4/5] w-full cursor-pointer place-items-center overflow-hidden rounded-lg border border-dashed border-glass-line bg-white/5 text-center transition-colors hover:border-primary"
          >
            {previewUrl ? (
              <Image
                src={previewUrl}
                alt="Selected photo preview"
                fill
                sizes="280px"
                unoptimized
                className="object-cover"
              />
            ) : (
              <span className="px-6 text-[13px] leading-relaxed text-ink-soft">
                <strong className="block text-[14px] text-ink">Choose a photo</strong>
                JPEG, PNG, or WebP · up to 20 MB
              </span>
            )}
            {previewUrl && (
              <span className="glass absolute right-2 bottom-2 rounded-full px-3 py-1 text-[11px] font-semibold">
                Change
              </span>
            )}
          </button>
          {file && <p className="mt-2 truncate text-[12px] text-ink-soft">{file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB</p>}
          {fileError && <p role="alert" className="mt-2 text-[12.5px] text-accent">{fileError}</p>}
        </div>

        <div>
          <label className="mb-4 block text-[13px] font-medium text-ink-soft">
            Caption
            <input
              value={caption}
              onChange={(event) => setCaption(event.target.value)}
              maxLength={300}
              placeholder="A little context for this photo"
              className="mt-1.5 w-full rounded-lg border border-glass-line bg-white/5 px-3.5 py-2.5 text-[13.5px] text-ink outline-none placeholder:text-ink-soft/50 focus:border-primary"
            />
          </label>
          <label className="mb-4 block text-[13px] font-medium text-ink-soft">
            Visible to
            <select
              value={visibility}
              onChange={(event) => setVisibility(event.target.value as PhotoVisibility)}
              className="mt-1.5 w-full rounded-lg border border-glass-line bg-[var(--bg-a)] px-3.5 py-2.5 text-[13.5px] text-ink outline-none focus:border-primary"
            >
              {VISIBILITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="mb-5 flex cursor-pointer items-center gap-2.5 text-[13px]">
            <input
              type="checkbox"
              checked={makePrimary}
              onChange={(event) => setMakePrimary(event.target.checked)}
              className="size-4 accent-[var(--primary)]"
            />
            Use as the primary profile photo
          </label>

          {upload.isError && (
            <p role="alert" className="mb-3 rounded-lg border border-accent/40 bg-accent-soft px-3 py-2 text-[12.5px]">
              {errorMessage(upload.error)}
            </p>
          )}
          <button
            type="button"
            disabled={!file || upload.isPending}
            onClick={() =>
              file && upload.mutate(
                { file, caption, visibility, isPrimary: makePrimary, onStage: setStage },
                { onSuccess: resetForm },
              )
            }
            className="bg-gradient-brand cursor-pointer rounded-full px-6 py-2.5 text-[13.5px] font-semibold text-on-primary transition-all hover:-translate-y-px hover:brightness-110 disabled:cursor-default disabled:opacity-40 disabled:hover:translate-y-0"
          >
            {upload.isPending ? stage ?? "Uploading…" : "Add photo"}
          </button>
        </div>
      </div>

      <div className="mt-8 border-t border-glass-line pt-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="font-display text-[16px] font-semibold">Your photos</h3>
          <span className="text-[12px] text-ink-soft">{photos.length} added</span>
        </div>
        {media.isLoading ? (
          <p className="text-[13px] text-ink-soft">Loading photos…</p>
        ) : photos.length === 0 ? (
          <p className="text-[13px] text-ink-soft">No photos added yet.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {photos.map((photo) => (
              <ExistingPhoto key={photo.id} profileId={profileId} photo={photo} />
            ))}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}