import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"

AppDialog {
    id:root
    signal importRequested(string path,string conflict)
    width:480; parent:Overlay.overlay; x:(parent.width-width)/2; y:(parent.height-height)/2; header:null; footer:null
    contentItem:ColumnLayout { spacing:Theme.spacing.md
        Text { text:"Import Template Package"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        InfoBanner { Layout.fillWidth:true; variant:"info"; text:".mmovtemplate packages are verified for safe paths, executable content, size limits and SHA-256 checksums before import." }
        RowLayout { Layout.fillWidth:true; AppTextField{id:path;Layout.fillWidth:true;placeholderText:"Choose .mmovtemplate"}; SecondaryButton{text:"Browse";onClicked:file.open()} }
        AppComboBox { id:conflict; Layout.fillWidth:true; model:["Keep Both","Replace","Cancel"] }
        RowLayout { Layout.fillWidth:true; Item{Layout.fillWidth:true}; SecondaryButton{text:"Close";onClicked:root.close()}; AppButton{text:"Import";onClicked:{var v=["keep_both","replace","cancel"][conflict.currentIndex];root.importRequested(path.text,v);root.close()}} }
    }
    FileDialog { id:file; title:"Import MMO Video Studio Template"; fileMode:FileDialog.OpenFile; nameFilters:["MMO Video Templates (*.mmovtemplate)"]; onAccepted:path.text=selectedFile.toString() }
}
