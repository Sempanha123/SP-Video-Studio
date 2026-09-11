import QtQuick 2.15
import QtQuick.Dialogs
import SPVideoStudio.Phase25 1.0
Item { id:root; property string assetId:""; FileDialog { id:picker; title:"Locate Missing Asset"; fileMode:FileDialog.OpenFile; onAccepted:AssetLibrary.relinkAsset(root.assetId,selectedFile,false) } function openFor(id){assetId=id;picker.open()} }
