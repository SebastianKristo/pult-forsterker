import { contextBridge, ipcRenderer } from 'electron';
import type { FlashProgress, FlashRequest } from '../shared/types';

contextBridge.exposeInMainWorld('skjold', {
  listDrives: () => ipcRenderer.invoke('drives:list'),
  latestImage: () => ipcRenderer.invoke('release:latest'),
  pickImage: () => ipcRenderer.invoke('image:pick'),
  flash: (req: FlashRequest) => ipcRenderer.invoke('flash:start', req),
  cancel: () => ipcRenderer.invoke('flash:cancel'),
  hostname: (name: string) => ipcRenderer.invoke('hostname', name),
  open: (url: string) => ipcRenderer.invoke('open', url),
  version: () => ipcRenderer.invoke('app:version'),
  platform: process.platform,
  onProgress: (cb: (p: FlashProgress) => void) => {
    const h = (_e: unknown, p: FlashProgress) => cb(p);
    ipcRenderer.on('flash:progress', h);
    return () => ipcRenderer.removeListener('flash:progress', h);
  },
});
