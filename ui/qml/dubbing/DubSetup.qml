import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"
AppCard {
    id:root
    required property var controller
    signal navigateRequested(string mode)
    property string sourceCode:"auto"
    property string targetCode:"km"
    implicitHeight:310
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.sm
        Text { text:"1 · Source video"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        AppComboBox { id:video; Layout.fillWidth:true; model:controller.sourceVideos; textRole:"name" }
        RowLayout { Layout.fillWidth:true
            ColumnLayout { Layout.fillWidth:true
                CheckBox { id:autoDetect; text:"Auto-detect source"; checked:true; onToggled:root.sourceCode=checked?"auto":sourcePicker.currentCode }
                LanguagePicker { id:sourcePicker; Layout.fillWidth:true; visible:!autoDetect.checked; currentCode:"en"; onCodeSelected:function(code){root.sourceCode=code} }
            }
            Text { text:"→"; color:Theme.colors.textMuted }
            LanguagePicker { id:targetPicker; Layout.fillWidth:true; currentCode:"km"; onCodeSelected:function(code){root.targetCode=code} }
        }
        InfoBanner { Layout.fillWidth:true; visible:root.sourceCode!=="auto"&&root.sourceCode===root.targetCode; variant:"warning"; text:"Source and target languages must differ." }
        AppButton { Layout.alignment:Qt.AlignRight; text:"Use Video"; enabled:video.currentIndex>=0&&(root.sourceCode==="auto"||root.sourceCode!==root.targetCode); onClicked:controller.updateSetup(video.model[video.currentIndex].id,root.sourceCode,root.targetCode) }
        Text { Layout.fillWidth:true; text:controller.project.sourceMediaId?"Source selected. Original video timing remains canonical.":"Choose an imported project video. Language support is validated by the selected engines."; color:Theme.colors.textSecondary; wrapMode:Text.Wrap }
        RowLayout { Layout.fillWidth:true; Item{Layout.fillWidth:true}; SecondaryButton{text:"Open Media";onClicked:root.navigateRequested("media")}; SecondaryButton{text:"Open Transcription";enabled:!!controller.project.sourceMediaId;onClicked:root.navigateRequested("transcription")} }
    }
}
