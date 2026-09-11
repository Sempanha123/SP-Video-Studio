import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root; property var snapshot: ({}); signal recoverRequested(string snapshotId); signal savedRequested(string snapshotId); signal reviewRequested(string snapshotId); signal discardRequested(string snapshotId)
    Layout.fillWidth: true; implicitHeight: content.implicitHeight + 28; elevated: true
    ColumnLayout { id: content; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
        RowLayout { Layout.fillWidth:true
            Rectangle { width:34;height:34;radius:10;color:Theme.colors.accentSoft; Icon{anchors.centerIn:parent;width:17;height:17;name:"projects"} }
            ColumnLayout { Layout.fillWidth:true; spacing:1
                Text { Layout.fillWidth:true; text: snapshot.projectTitle || snapshot.projectId || "Project"; elide:Text.ElideRight; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                Text { text: "Recovered " + (snapshot.createdAt || "") + " · revision " + (snapshot.projectRevision || 0); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
            StatusBadge { text:"Recovery found";status:"warning" }
        }
        Text { visible:(snapshot.missingMedia||0)>0; text:"Recovered with missing media. You can relink those files after opening the project."; color:Theme.colors.warning; wrapMode:Text.WordWrap; Layout.fillWidth:true; font.family:Theme.type.family; font.pixelSize:Theme.type.small }
        RowLayout { spacing:Theme.spacing.sm;Layout.fillWidth:true
            AppButton{text:"Recover";onClicked:root.recoverRequested(String(snapshot.id||""))}
            AppButton{text:"Open Saved Version";variant:"secondary";onClicked:root.savedRequested(String(snapshot.id||""))}
            AppButton{text:"Review";variant:"quiet";onClicked:root.reviewRequested(String(snapshot.id||""))}
            Item{Layout.fillWidth:true}
            AppButton{text:"Discard";variant:"danger";size:"small";onClicked:root.discardRequested(String(snapshot.id||""))}
        }
    }
}
