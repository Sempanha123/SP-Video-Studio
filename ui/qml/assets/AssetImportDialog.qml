import QtQuick 2.15
import QtQuick.Dialogs
import SPVideoStudio.Phase25 1.0
Item {
    id:root
    property bool managed:true
    FileDialog { id:picker; title:root.managed?"Copy into Asset Library":"Reference Original File"; fileMode:FileDialog.OpenFile; nameFilters:["Media Files (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.jpg *.jpeg *.png *.webp *.bmp)"]; onAccepted:AssetLibrary.importAsset(selectedFile,root.managed,"general","use_existing") }
    function openManaged(){managed=true;picker.open()}
    function openReferenced(){managed=false;picker.open()}
}
