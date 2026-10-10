param([object]$ScreensFolderItem, [string]$LocalCopyDir)
# Deletes the screenshot JPEGs in sdmc:/switch/Mercenaries2/logs/screens over MTP (user request:
# do not let screenshots fill the SD card). Only *.jpg directly in a folder named "screens", and
# only those already present with the same size in $LocalCopyDir (the run capture).
$ErrorActionPreference='Stop'
if(!$ScreensFolderItem -or $ScreensFolderItem.Name -ne 'screens'){throw 'Expected screens folder'}
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
[ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface M2ShellItemD {}
[ComImport, Guid("947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface M2FileOperationD {
 [PreserveSig] int Advise(IntPtr s,out uint c);
 [PreserveSig] int Unadvise(uint c);
 [PreserveSig] int SetOperationFlags(uint f);
 [PreserveSig] int SetProgressMessage([MarshalAs(UnmanagedType.LPWStr)]string s);
 [PreserveSig] int SetProgressDialog(IntPtr p);
 [PreserveSig] int SetProperties(IntPtr p);
 [PreserveSig] int SetOwnerWindow(uint w);
 [PreserveSig] int ApplyPropertiesToItem(M2ShellItemD s);
 [PreserveSig] int ApplyPropertiesToItems(IntPtr s);
 [PreserveSig] int RenameItem(M2ShellItemD s,[MarshalAs(UnmanagedType.LPWStr)]string n,IntPtr p);
 [PreserveSig] int RenameItems(IntPtr s,[MarshalAs(UnmanagedType.LPWStr)]string n);
 [PreserveSig] int MoveItem(M2ShellItemD s,M2ShellItemD d,[MarshalAs(UnmanagedType.LPWStr)]string n,IntPtr p);
 [PreserveSig] int MoveItems(IntPtr s,M2ShellItemD d);
 [PreserveSig] int CopyItem(M2ShellItemD s,M2ShellItemD d,[MarshalAs(UnmanagedType.LPWStr)]string n,IntPtr p);
 [PreserveSig] int CopyItems(IntPtr s,M2ShellItemD d);
 [PreserveSig] int DeleteItem(M2ShellItemD s,IntPtr p);
 [PreserveSig] int DeleteItems(IntPtr s);
 [PreserveSig] int NewItem(M2ShellItemD d,uint a,[MarshalAs(UnmanagedType.LPWStr)]string n,[MarshalAs(UnmanagedType.LPWStr)]string t,IntPtr p);
 [PreserveSig] int PerformOperations();
 [PreserveSig] int GetAnyOperationsAborted([MarshalAs(UnmanagedType.Bool)]out bool a);
}
public class M2Delete {
 [DllImport("shell32.dll",PreserveSig=true)] static extern int SHGetIDListFromObject([MarshalAs(UnmanagedType.IUnknown)] object item,out IntPtr pidl);
 [DllImport("shell32.dll",PreserveSig=true)] static extern int SHCreateItemFromIDList(IntPtr pidl,ref Guid iid,out M2ShellItemD item);
 public static int Delete(object[] items) {
  Guid iid=new Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE");
  var op=(M2FileOperationD)Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("3AD05575-8857-4850-9277-11B85BDB8E09")));
  // FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_NOCONFIRMMKDIR; no FOF_ALLOWUNDO (MTP has no bin).
  Marshal.ThrowExceptionForHR(op.SetOperationFlags(4|16|1024|512));
  foreach (object item in items) {
   IntPtr pidl; Marshal.ThrowExceptionForHR(SHGetIDListFromObject(item,out pidl));
   M2ShellItemD s; try { Marshal.ThrowExceptionForHR(SHCreateItemFromIDList(pidl,ref iid,out s)); } finally { Marshal.FreeCoTaskMem(pidl); }
   Marshal.ThrowExceptionForHR(op.DeleteItem(s,IntPtr.Zero));
  }
  int result=op.PerformOperations(); Marshal.ThrowExceptionForHR(result);
  bool aborted; Marshal.ThrowExceptionForHR(op.GetAnyOperationsAborted(out aborted));
  if(aborted) throw new Exception("MTP delete aborted");
  return items.Length;
 }
}
"@
$items = @()
foreach ($it in $ScreensFolderItem.GetFolder.Items()) {
  if ($it.Name -notmatch '^\d{8}_\d{6}(_\w+)?\.jpg$') { continue }
  $local = Join-Path $LocalCopyDir $it.Name
  if (!(Test-Path $local)) { Write-Output "keep (no local copy): $($it.Name)"; continue }
  $items += $it
}
if ($items.Count) { "deleted $([M2Delete]::Delete([object[]]$items)) screenshots" } else { 'nothing to delete' }
