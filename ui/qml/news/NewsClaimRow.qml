import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Rectangle {
    id: root
    property var controller
    property var claim: ({})
    implicitHeight: 116; radius: Theme.radius.medium; color: Theme.colors.surface2; border.color: Theme.colors.border
    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: 5
        RowLayout { Layout.fillWidth:true; StatusBadge { text: root.claim.status || "candidate"; status: root.claim.status==="approved"?"ready":(root.claim.status==="unsupported"||root.claim.status==="conflicting"?"error":"warning") }; Text { text: root.claim.type || "fact"; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption }; Item { Layout.fillWidth:true }; Text { text:(root.claim.sourceCount||0)+" source(s)"; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption } }
        Text { Layout.fillWidth:true; text:root.claim.text||""; wrapMode:Text.WordWrap; maximumLineCount:2; elide:Text.ElideRight; color:Theme.colors.textPrimary }
        RowLayout { Layout.fillWidth:true; SecondaryButton { text:root.claim.locked?"Unlock":"Lock"; compact:true; onClicked:root.controller.lockClaim(root.claim.id,!root.claim.locked) }; Item { Layout.fillWidth:true }; SecondaryButton { text:"Reject"; compact:true; onClicked:root.controller.rejectClaim(root.claim.id) }; AppButton { text:"Approve"; compact:true; enabled:root.claim.status!=="approved"; onClicked:root.controller.approveClaim(root.claim.id,"") } }
    }
}
