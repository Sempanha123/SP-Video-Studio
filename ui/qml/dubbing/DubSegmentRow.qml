import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"
Rectangle {
    id:root
    required property var controller
    required property var segment
    color: Theme.colors.surface; border.color: Theme.colors.border; radius: Theme.radius.medium; height: Math.max(142, Math.round(142*Theme.textScale))
    function time(ms) { var s=Math.max(0,Number(ms||0))/1000; return s.toFixed(3)+"s" }
    function timingLabel() { var status=String(segment.timingStatus||"pending").replaceAll("_"," "); var delta=Number(segment.generatedDurationMs||0)-Number(segment.targetDurationMs||0); if(Number(segment.generatedDurationMs||0)>0&&Number(segment.targetDurationMs||0)>0&&Math.abs(delta)>=100) return (delta>=0?"+":"")+(delta/1000).toFixed(1)+" seconds " +(delta>0?"long":"short"); return status }
    Accessible.role: Accessible.ListItem
    Accessible.name: (segment.speakerLabel || "Narrator") + ". " + root.timingLabel() + ". " + (segment.targetText || "Translation missing")
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.xs
        RowLayout { Layout.fillWidth:true
            Text { text:time(segment.sourceStartMs)+" → "+time(segment.sourceEndMs); color:Theme.colors.textMuted; font.family:Theme.type.family }
            Text { text:segment.speakerLabel || "Narrator"; color:Theme.colors.textSecondary }
            Item { Layout.fillWidth:true }
            StatusBadge { text:root.timingLabel(); status:String(segment.timingStatus||"pending").indexOf("fit")>=0?"ready":(String(segment.timingStatus||"pending").indexOf("fail")>=0?"error":"warning") }
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
    AppDialog { id:timing; modal:true; onOpened:Commands.setModalOpen(true); onClosed:Commands.setModalOpen(false); parent:Overlay.overlay; x:(parent.width-width)/2; y:(parent.height-height)/2; title:"Dub timing"; width:480
        contentItem: DubTimingInspector { controller:root.controller; segment:root.segment; onDone:timing.close() }
    }
}
