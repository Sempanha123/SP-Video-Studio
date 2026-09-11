import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
ColumnLayout {
    id:root
    required property var controller
    required property var segment
    signal done()
    spacing:Theme.spacing.md
    Text { text:"Source: "+segment.sourceStartMs+"–"+segment.sourceEndMs+" ms"; color:Theme.colors.textSecondary }
    Text { text:"Generated: "+segment.generatedDurationMs+" ms · target: "+segment.targetDurationMs+" ms"; color:Theme.colors.textSecondary }
    ComboBox { id:mode; model:["natural","fit_segment","extend_segment"]; currentIndex:Math.max(0,model.indexOf(segment.timingMode)) }
    SpinBox { id:offset; from:-60000; to:60000; value:Number(segment.startOffsetMs||0); editable:true }
    Text { visible:segment.timingStatus==="needs_review" || segment.timingStatus==="very_long"; text:"This segment is too long to fit naturally. Consider shortening the translation, regenerating, or extending timing."; wrapMode:Text.Wrap; color:Theme.colors.textSecondary; Layout.fillWidth:true }
    RowLayout { Item { Layout.fillWidth:true }; SecondaryButton { text:"Cancel"; onClicked:root.done() }; AppButton { text:"Apply"; onClicked:{ if(controller.updateTiming(segment.id,mode.currentText,offset.value,false)) root.done() } } }
}
