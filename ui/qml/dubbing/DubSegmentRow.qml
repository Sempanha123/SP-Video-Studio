import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Rectangle {
    id:root
    required property var controller
    required property var segment
    color: Theme.colors.surface; border.color: Theme.colors.border; radius: Theme.radius.medium; height: 142
    function time(ms) { var s=Math.max(0,Number(ms||0))/1000; return s.toFixed(3)+"s" }
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.xs
        RowLayout { Layout.fillWidth:true
            Text { text:time(segment.sourceStartMs)+" → "+time(segment.sourceEndMs); color:Theme.colors.textMuted; font.family:Theme.type.family }
            Text { text:segment.speakerLabel || "Narrator"; color:Theme.colors.textSecondary }
            Item { Layout.fillWidth:true }
            Text { text:(segment.timingStatus||"pending").replace("_"," "); color:Theme.colors.textSecondary }
        }
        Text { Layout.fillWidth:true; text:segment.targetText || "Translation missing"; color:Theme.colors.textPrimary; wrapMode:Text.Wrap; maximumLineCount:2; elide:Text.ElideRight }
        RowLayout { Layout.fillWidth:true
            Text { text:"Audio "+time(segment.generatedDurationMs)+" / Target "+time(segment.targetDurationMs); color:Theme.colors.textMuted }
            Item { Layout.fillWidth:true }
            CheckBox { text:"Lock"; checked:!!segment.locked; onToggled:controller.lockSegment(segment.id,checked) }
            SecondaryButton { text:"Timing"; compact:true; onClicked:timing.open() }
            AppButton { text:"Regenerate"; compact:true; enabled:!segment.locked; onClicked:controller.generateSelected([segment.id]) }
        }
    }
    Dialog { id:timing; modal:true; parent:Overlay.overlay; x:(parent.width-width)/2; y:(parent.height-height)/2; title:"Dub timing"; width:480
        contentItem: DubTimingInspector { controller:root.controller; segment:root.segment; onDone:timing.close() }
    }
}
