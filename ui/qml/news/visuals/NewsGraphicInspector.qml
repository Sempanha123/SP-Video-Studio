import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
AppCard {
    id: root
    property var controller
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.sm
        SectionHeader { title: "Graphic Inspector"; subtitle: "Provenance and layout state stay visible while the generic Scene overlay owns geometry." }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true
            ColumnLayout { width: parent.width; spacing: Theme.spacing.xs
                Repeater { model: root.controller ? root.controller.elements : []
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: detail.implicitHeight + Theme.spacing.md*2; radius: Theme.radius.small; color: Theme.colors.surfaceHover; border.color: Theme.colors.border
                        ColumnLayout { id: detail; anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: 4
                            RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: (modelData.graphicType||"Graphic").replace("_"," "); color: Theme.colors.textPrimary; font.weight: Font.DemiBold }; StatusBadge { text: modelData.status||"current"; status: modelData.status==="unsupported_source"?"error":(modelData.status==="source_changed"?"warning":"ready") } }
                            Text { Layout.fillWidth: true; elide: Text.ElideRight; text: modelData.claimId ? "Based on claim • "+modelData.claimId.slice(0,8) : (modelData.sourceId ? "Source-linked" : "Manual / decorative"); color: Theme.colors.textMuted; font.pixelSize: Theme.type.caption }
                            RowLayout { Layout.fillWidth: true; visible: modelData.status==="source_changed" && (modelData.claimId||"")!==""; SecondaryButton { text: "Update from Claim"; compact: true; onClicked: root.controller.updateFromClaim(modelData.id) }; Item { Layout.fillWidth:true } }
                            Repeater { model: modelData.issues || []; Text { Layout.fillWidth:true; wrapMode:Text.WordWrap; text:"• "+modelData.message; color: modelData.severity==="error"?Theme.colors.danger:Theme.colors.warning; font.pixelSize:Theme.type.caption } }
                        }
                    }
                }
            }
        }
    }
}
