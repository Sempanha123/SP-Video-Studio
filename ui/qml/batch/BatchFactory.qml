import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item {
    id: root
    property var controller; property int step: 0; property var mappings: []; property var variants: ({}); property string batchName: "New Batch"; property string templateId: ""; property string outputFolder: ""; property var selectedItem: ({})
    Timer { interval: 900; repeat: true; running: root.step === 5; onTriggered: if(root.controller) root.controller.refresh() }
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.md
        PageHeader { Layout.fillWidth: true; title: "Batch Factory"; description: "Create many videos from one template without turning the queue into a spreadsheet.";
            actions: [AppComboBox { id: history; Layout.preferredWidth: 210; model: root.controller ? root.controller.batches : []; textRole: "name"; valueRole: "id"; onActivated: if(currentValue) root.controller.openBatch(currentValue) }]
        }
        WorkflowStepper { Layout.fillWidth: true; steps: ["Template","Data","Mapping","Variants","Review","Run"]; currentIndex: root.step; onStepRequested: function(index){ if(index <= root.step) root.step=index } }
        StackLayout { Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: root.step
            BatchSetup { controller:root.controller; batchName:root.batchName; templateId:root.templateId; outputFolder:root.outputFolder; onNextRequested:{ root.batchName=batchName; root.templateId=templateId; root.outputFolder=outputFolder; root.step=1 } }
            BatchInputTable { controller:root.controller; onNextRequested:root.step=2 }
            BatchMapping { controller:root.controller; templateId:root.templateId; onNextRequested:{ root.mappings=mappings; root.step=3 } }
            BatchVariantPanel { controller:root.controller; onNextRequested:{ root.variants=config; root.step=4 } }
            Item { ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.lg
                Text { text:"Review before running"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.sectionTitle; font.weight:Theme.type.semibold }
                Text { text:"Dry Run resolves mappings, languages, voices, reusable Assets and safe output paths without creating projects or rendering."; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; wrapMode:Text.WordWrap; Layout.fillWidth:true }
                AppCard { Layout.fillWidth:true; Layout.preferredHeight:72
                    RowLayout { anchors.fill:parent; anchors.margins:Theme.spacing.md; spacing:Theme.spacing.xl
                        ColumnLayout { Text{text:String(controller.dryRunSummary.total||0);color:Theme.colors.textPrimary;font.pixelSize:Theme.type.heading;font.weight:Theme.type.semibold} Text{text:"Outputs";color:Theme.colors.textMuted;font.pixelSize:Theme.type.caption} }
                        ColumnLayout { Text{text:String(controller.dryRunSummary.invalid||0);color:(controller.dryRunSummary.invalid||0)>0?Theme.colors.danger:Theme.colors.textPrimary;font.pixelSize:Theme.type.heading;font.weight:Theme.type.semibold} Text{text:"Invalid";color:Theme.colors.textMuted;font.pixelSize:Theme.type.caption} }
                        ColumnLayout { Text{text:String(controller.dryRunSummary.warnings||0);color:Theme.colors.warning;font.pixelSize:Theme.type.heading;font.weight:Theme.type.semibold} Text{text:"Warnings";color:Theme.colors.textMuted;font.pixelSize:Theme.type.caption} }
                        Item{Layout.fillWidth:true}
                    }
                }
                RowLayout { AppButton { text:"Create Batch"; onClicked:{ var id=controller.createBatch(root.batchName,root.templateId,root.outputFolder,root.mappings,root.variants,{translation_policy:"reviewed_only",collision_policy:"keep_both",performance_profile:"balanced"}); if(id)controller.validateBatch() } }; AppButton{text:"Validate / Dry Run";variant:"secondary";enabled:!!controller.currentBatch.id;onClicked:controller.validateBatch()}; Item{Layout.fillWidth:true}; AppButton{text:"Prepare Queue";variant:"secondary";enabled:(controller.dryRunSummary.invalid||0)===0;onClicked:controller.prepareQueue(false)}; AppButton{text:"Start Batch";enabled:controller.currentBatch.totalItems>0;onClicked:{controller.runBatch();root.step=5}} }
                Item { Layout.fillHeight:true }
            } }
            Item { ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.sm
                BatchProgress { Layout.fillWidth:true; Layout.preferredHeight:60; controller:root.controller }
                SplitView { Layout.fillWidth:true; Layout.fillHeight:true
                    BatchQueue { SplitView.fillWidth:true; SplitView.minimumWidth:520; controller:root.controller; onItemSelected:root.selectedItem=itemData }
                    ScrollView { SplitView.preferredWidth:320; SplitView.minimumWidth:270; ColumnLayout { width:parent.width; spacing:Theme.spacing.md; BatchDetails{Layout.fillWidth:true;Layout.preferredHeight:320;itemData:root.selectedItem;controller:root.controller} BatchErrorPanel{Layout.fillWidth:true;Layout.preferredHeight:180;itemData:root.selectedItem} } }
                }
            } }
        }
    }
}
