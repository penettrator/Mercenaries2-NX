param([string]$Source,[object]$DestinationShellItem)
# Call only after explicit approval to copy this exact NRO to the console.
# Success HRESULT does not replace a read-back hash check.
$ErrorActionPreference='Stop'
if(!(Test-Path -LiteralPath $Source -PathType Leaf)){throw 'Source NRO absent'}
if([IO.Path]::GetExtension($Source) -ne '.nro'){throw 'Expected NRO source'}
if(!$DestinationShellItem -or $DestinationShellItem.Name -ne 'Mercenaries2'){throw 'Expected Mercenaries2 destination folder'}
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
[ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface M2ShellItem {}
[ComImport, Guid("947AAB5F-0A5C-4C13-B4D6-4BF7836FC9F8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface M2FileOperation {
 [PreserveSig] int Advise(IntPtr s,out uint c);
 [PreserveSig] int Unadvise(uint c);
 [PreserveSig] int SetOperationFlags(uint f);
 [PreserveSig] int SetProgressMessage([MarshalAs(UnmanagedType.LPWStr)]string s);
 [PreserveSig] int SetProgressDialog(IntPtr p);
 [PreserveSig] int SetProperties(IntPtr p);
 [PreserveSig] int SetOwnerWindow(uint w);
 [PreserveSig] int ApplyPropertiesToItem(M2ShellItem s);
 [PreserveSig] int ApplyPropertiesToItems(IntPtr s);
 [PreserveSig] int RenameItem(M2ShellItem s,[MarshalAs(UnmanagedType.LPWStr)]string n,IntPtr p);
 [PreserveSig] int RenameItems(IntPtr s,[MarshalAs(UnmanagedType.LPWStr)]string n);
 [PreserveSig] int MoveItem(M2ShellItem s,M2ShellItem d,[MarshalAs(UnmanagedType.LPWStr)]string n,IntPtr p);
 [PreserveSig] int MoveItems(IntPtr s,M2ShellItem d);
 [PreserveSig] int CopyItem(M2ShellItem s,M2ShellItem d,[MarshalAs(UnmanagedType.LPWStr)]string n,IntPtr p);
 [PreserveSig] int CopyItems(IntPtr s,M2ShellItem d);
 [PreserveSig] int DeleteItem(M2ShellItem s,IntPtr p);
 [PreserveSig] int DeleteItems(IntPtr s);
 [PreserveSig] int NewItem(M2ShellItem d,uint a,[MarshalAs(UnmanagedType.LPWStr)]string n,[MarshalAs(UnmanagedType.LPWStr)]string t,IntPtr p);
 [PreserveSig] int PerformOperations();
 [PreserveSig] int GetAnyOperationsAborted([MarshalAs(UnmanagedType.Bool)]out bool a);
}
public class M2Copy {
 [DllImport("shell32.dll",CharSet=CharSet.Unicode,PreserveSig=true)]
 static extern int SHCreateItemFromParsingName(string path,IntPtr context,ref Guid iid,out M2ShellItem item);
 [DllImport("shell32.dll",PreserveSig=true)] static extern int SHGetIDListFromObject([MarshalAs(UnmanagedType.IUnknown)] object item,out IntPtr pidl);
 [DllImport("shell32.dll",PreserveSig=true)] static extern int SHCreateItemFromIDList(IntPtr pidl,ref Guid iid,out M2ShellItem item);
 public static void Copy(string source,object destination) {
  Guid iid=new Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE");M2ShellItem s,d;
  Console.WriteLine("Stage source parsing"); Marshal.ThrowExceptionForHR(SHCreateItemFromParsingName(source,IntPtr.Zero,ref iid,out s));
  IntPtr pidl; Marshal.ThrowExceptionForHR(SHGetIDListFromObject(destination,out pidl));
  try { Marshal.ThrowExceptionForHR(SHCreateItemFromIDList(pidl,ref iid,out d)); } finally { Marshal.FreeCoTaskMem(pidl); }
  var op=(M2FileOperation)Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("3AD05575-8857-4850-9277-11B85BDB8E09")));
  Console.WriteLine("Stage flags"); Marshal.ThrowExceptionForHR(op.SetOperationFlags(4|16|512|1024));
  Console.WriteLine("Stage enqueue copy"); Marshal.ThrowExceptionForHR(op.CopyItem(s,d,"mercenaries2.nro",IntPtr.Zero));
  int result=op.PerformOperations(); Console.WriteLine("PerformOperations HRESULT=0x"+result.ToString("X8"));
  Marshal.ThrowExceptionForHR(result);bool aborted;Marshal.ThrowExceptionForHR(op.GetAnyOperationsAborted(out aborted));
  Console.WriteLine("Aborted="+aborted);if(aborted)throw new Exception("MTP file operation aborted");
 }
}
"@
[M2Copy]::Copy($Source,$DestinationShellItem)
