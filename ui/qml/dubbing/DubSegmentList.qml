import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root
    required property var controller
    property string filter: "all"
    implicitHeight: Math.min(620, Math.max(220, list.contentHeight + 120))
    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
        RowLayout { Layout.fillWidth: true
            Text { text: "5 · Dub segments"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Sync Translation"; onClicked: controller.syncTranslation() }
            SecondaryButton { visible:controller.busy; text:"Cancel"; onClicked:controller.cancelGeneration() }
            AppButton { text: controller.busy ? "Generating…" : "Generate Dub Audio"; enabled:!controller.busy; onClicked: controller.generateAll() }
        }
        RowLayout { Layout.fillWidth: true
            Repeater { model: ["all","ready","long","short","needs_review","outdated","failed","locked"]
                delegate: Button { required property string modelData; text: modelData.replace("_"," "); checkable: true; checked: root.filter===modelData; onClicked: root.filter=modelData }
            }
        }
        ListView { id:list; Layout.fillWidth:true; Layout.fillHeight:true; implicitHeight: 360; clip:true; spacing:Theme.spacing.xs
            model: controller.segments
            delegate: DubSegmentRow { width:list.width; controller:root.controller; segment:modelData; visible: root.filter==="all" || (root.filter==="locked" ? !!modelData.locked : modelData.audioStatus===root.filter || modelData.timingStatus===root.filter) }
        }
    }
}
