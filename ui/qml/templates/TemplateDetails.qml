import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

ColumnLayout {
    id:root; property var templateData:({}); signal useRequested(); signal duplicateRequested(); signal deleteRequested(); signal exportRequested()
    spacing:Theme.spacing.sm
    Text { text:"Components"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; font.weight:Theme.type.semibold }
    Repeater { model:templateData.components || []; delegate:RowLayout { required property var modelData; Layout.fillWidth:true; Text{Layout.fillWidth:true;text:String(modelData.type||"").replaceAll("_"," ");color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption}; StatusBadge{text:"Included";status:"success"} } }
    RowLayout { Layout.fillWidth:true; AppButton{text:"Use Template";onClicked:root.useRequested()}; SecondaryButton{text:"Duplicate";onClicked:root.duplicateRequested()}; SecondaryButton{visible:!templateData.builtin;text:"Export";onClicked:root.exportRequested()}; SecondaryButton{visible:!templateData.builtin;text:"Delete";onClicked:root.deleteRequested()} }
}
